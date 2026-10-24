"""공식 TFLite 그래프를 ONNX로 변환하고 CPU 대체 없는 CUDA 실행을 검증한다."""
from pathlib import Path
import json
import sys
import os
import subprocess
import time
import threading
from datetime import datetime

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
MODEL_SOURCE_DIRECTORY = WORKFLOW_ROOT_DIRECTORY/'.model/music/music-magenta/source/resources/musiccoca'
MODEL_OUTPUT_DIRECTORY = WORKFLOW_ROOT_DIRECTORY/'.model/music/music-magenta/onnx'
VERIFICATION_OUTPUT_DIRECTORY = WORKFLOW_ROOT_DIRECTORY/'.tmp/test/magenta-gpu-encoder'


def emit_validation_heartbeat(current_stop_event):
    while not current_stop_event.wait(5):
        print(f'{datetime.now().isoformat()}/magenta/heartbeat GPU 인코더 검증 진행 중',flush=True)


def convert_encoder_graph(current_model_name):
    import numpy
    import tf2onnx
    from tf2onnx.handler import tfl_op
    from tf2onnx.tflite_handlers.tfl_math import TflFullyConnectedOp, separate_fused_activation_function
    current_original_handler = TflFullyConnectedOp.to_tf

    @tfl_op(['TFL_FULLY_CONNECTED'])
    class PreserveFullyConnectedDimensions:
        @classmethod
        def to_tf(cls, current_graph_context, current_graph_node, **current_handler_options):
            if not current_graph_node.attr['keep_num_dims'].i:
                return current_original_handler(current_graph_context,current_graph_node,**current_handler_options)
            if current_graph_node.attr['weights_format'].s != b'DEFAULT' or current_graph_node.attr['asymmetric_quantize_inputs'].i:
                raise ValueError('지원하지 않는 FullyConnected 가중치 형식')
            separate_fused_activation_function(current_graph_context,current_graph_node)
            current_weight_node = current_graph_context.insert_new_node_on_input(current_graph_node,'Transpose',current_graph_node.input[1],name=None,input_index=1,perm=[1,0])
            current_weight_node.skip_conversion = True
            current_graph_node.type = 'MatMul'
            current_graph_node.skip_conversion = True
            if len(current_graph_node.input)==3:
                current_bias_input = current_graph_node.input[2]
                current_graph_context.replace_inputs(current_graph_node,current_graph_node.input[:2])
                current_bias_node = current_graph_context.insert_new_node_on_output('Add',current_graph_node.output[0],inputs=[current_graph_node.output[0],current_bias_input])
                current_bias_node.skip_conversion = True
            for current_attribute_name in list(current_graph_node.attr):
                del current_graph_node.attr[current_attribute_name]
    @tfl_op(['TFL_EMBEDDING_LOOKUP'])
    class ConvertEmbeddingLookup:
        @classmethod
        def to_tf(cls, current_graph_context, current_graph_node, **current_handler_options):
            current_graph_context.replace_inputs(current_graph_node,[current_graph_node.input[1],current_graph_node.input[0]])
            current_graph_node.type = 'Gather'
            current_graph_node.set_attr('axis',0)
            current_graph_node.skip_conversion = True

    @tfl_op(['TFL_GELU'])
    class ConvertGaussianActivation:
        @classmethod
        def to_tf(cls, current_graph_context, current_graph_node, **current_handler_options):
            current_input_name = current_graph_node.input[0]
            def create_constant_node(current_constant_value):
                return current_graph_context.make_const(tf2onnx.utils.make_name('gelu_constant'),numpy.array(current_constant_value,dtype=numpy.float32)).output[0]
            def create_operator_node(current_operator_name,current_input_names):
                current_created_node = current_graph_context.make_node(current_operator_name,current_input_names)
                current_created_node.skip_conversion = True
                return current_created_node.output[0]
            if current_graph_node.get_attr_value('approximate',0):
                current_cube_value = create_operator_node('Pow',[current_input_name,create_constant_node(3)])
                current_scaled_cube = create_operator_node('Mul',[current_cube_value,create_constant_node(0.044715)])
                current_inner_value = create_operator_node('Add',[current_input_name,current_scaled_cube])
                current_scaled_value = create_operator_node('Mul',[current_inner_value,create_constant_node(numpy.sqrt(2/numpy.pi))])
                current_activation_value = create_operator_node('Tanh',[current_scaled_value])
            else:
                current_scaled_value = create_operator_node('Div',[current_input_name,create_constant_node(numpy.sqrt(2))])
                current_activation_value = create_operator_node('Erf',[current_scaled_value])
            current_plus_value = create_operator_node('Add',[current_activation_value,create_constant_node(1)])
            current_half_value = create_operator_node('Mul',[current_input_name,create_constant_node(0.5)])
            current_graph_context.replace_inputs(current_graph_node,[current_half_value,current_plus_value])
            current_graph_node.type = 'Mul'
            current_graph_node.skip_conversion = True
            for current_attribute_name in list(current_graph_node.attr):
                del current_graph_node.attr[current_attribute_name]

    current_output_path = MODEL_OUTPUT_DIRECTORY/(current_model_name+'.onnx')
    current_onnx_model, _ = tf2onnx.convert.from_tflite(str(MODEL_SOURCE_DIRECTORY/(current_model_name+'.tflite')),opset=17,output_path=str(current_output_path))
    if current_model_name == 'mapper':
        import onnx
        current_original_output = current_onnx_model.graph.output[0].name
        current_normalized_output = current_original_output+'_normalized'
        current_onnx_model.graph.node.append(onnx.helper.make_node('ReduceL2',[current_original_output],[current_original_output+'_norm'],axes=[-1],keepdims=1))
        current_onnx_model.graph.node.append(onnx.helper.make_node('Div',[current_original_output,current_original_output+'_norm'],[current_normalized_output]))
        current_onnx_model.graph.output[0].name = current_normalized_output
        onnx.save(current_onnx_model,str(current_output_path))
    return current_output_path


def verify_encoder_cuda():
    import numpy
    import onnxruntime
    sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
    from tools.review.common.generation_telemetry import GenerationTelemetryRecorder
    import sentencepiece
    MODEL_OUTPUT_DIRECTORY.mkdir(parents=True,exist_ok=True)
    VERIFICATION_OUTPUT_DIRECTORY.mkdir(parents=True,exist_ok=True)
    current_metrics_recorder = GenerationTelemetryRecorder(VERIFICATION_OUTPUT_DIRECTORY,3,[])
    current_metrics_recorder.start_generation_telemetry()
    current_stop_event = threading.Event()
    threading.Thread(target=emit_validation_heartbeat,args=(current_stop_event,),daemon=True).start()
    current_validation_record = {'status':'running','cpu_fallback_allowed':False,'models':{}}
    (VERIFICATION_OUTPUT_DIRECTORY/'result.json').write_text(json.dumps(current_validation_record))
    try:
        current_metrics_recorder.update_generation_stage('inference')
        onnxruntime.preload_dlls(directory='')
        if 'CUDAExecutionProvider' not in onnxruntime.get_available_providers():
            raise RuntimeError('ONNX CUDA provider가 없습니다.')
        current_tokenizer_model = sentencepiece.SentencePieceProcessor(model_file=str(MODEL_SOURCE_DIRECTORY/'spm.model'))
        current_token_ids = [1]+current_tokenizer_model.encode('peaceful acoustic village music with harp and wooden flute')[:127]
        current_input_tokens = numpy.array([current_token_ids+[0]*(128-len(current_token_ids))],dtype=numpy.int32)
        current_input_padding = numpy.array([[0.]*len(current_token_ids)+[1.]*(128-len(current_token_ids))],dtype=numpy.float32)
        current_embedding_value = None
        for current_model_name in ('text_encoder','mapper','pretrained_vector_quantizer'):
            print(f'{datetime.now().isoformat()}/magenta/convert {current_model_name}',flush=True)
            current_model_path = convert_encoder_graph(current_model_name)
            current_session_options = onnxruntime.SessionOptions()
            current_session_options.add_session_config_entry('session.disable_cpu_ep_fallback','1')
            current_session_options.enable_profiling = True
            current_session_options.profile_file_prefix = str(VERIFICATION_OUTPUT_DIRECTORY/current_model_name)
            current_model_session = onnxruntime.InferenceSession(str(current_model_path),sess_options=current_session_options,providers=['CUDAExecutionProvider'])
            current_model_inputs = {}
            for current_input_index,current_input_record in enumerate(current_model_session.get_inputs()):
                if current_model_name=='text_encoder':
                    current_input_value = current_input_tokens if current_input_record.type=='tensor(int32)' else current_input_padding
                elif current_model_name=='mapper':
                    current_input_value = current_embedding_value if current_input_index==0 else numpy.random.RandomState(7).randn(*current_embedding_value.shape).astype(numpy.float32)
                else:
                    current_input_value = current_embedding_value
                current_model_inputs[current_input_record.name] = current_input_value.reshape(current_input_record.shape)
            current_started_time = time.monotonic()
            current_output_values = current_model_session.run(None,current_model_inputs)
            current_profile_path = current_model_session.end_profiling()
            current_profile_events = json.loads(Path(current_profile_path).read_text())
            current_provider_counts = {}
            for current_event_record in current_profile_events:
                current_provider_name = current_event_record.get('args',{}).get('provider')
                if current_provider_name:
                    current_provider_counts[current_provider_name] = current_provider_counts.get(current_provider_name,0)+1
            if set(current_provider_counts) != {'CUDAExecutionProvider'}:
                raise RuntimeError(f'GPU 외 연산 발견: {current_provider_counts}')
            if not all(numpy.isfinite(current_output_value).all() for current_output_value in current_output_values):
                raise ValueError('출력에 비유한값 발생')
            current_validation_record['models'][current_model_name] = {'shapes':[list(current_output_value.shape) for current_output_value in current_output_values],'providers':current_provider_counts,'elapsed_seconds':time.monotonic()-current_started_time}
            if current_model_name!='pretrained_vector_quantizer':
                current_embedding_value = current_output_values[0]
            numpy.savez(VERIFICATION_OUTPUT_DIRECTORY/(current_model_name+'-outputs.npz'),*current_output_values)
            current_metrics_recorder.record_generation_step(len(current_validation_record['models']))
            del current_model_session
        current_validation_record['status']='passed'
    except Exception as current_validation_error:
        current_validation_record.update(status='failed',error=str(current_validation_error))
        raise
    finally:
        current_stop_event.set()
        current_metrics_recorder.finish_generation_telemetry('completed' if current_validation_record['status']=='passed' else 'failed')
        (VERIFICATION_OUTPUT_DIRECTORY/'result.json').write_text(json.dumps(current_validation_record,ensure_ascii=False,indent=2))


if __name__=='__main__':
    current_library_root = Path(sys.prefix)/'lib/python3.11/site-packages/nvidia'
    if os.environ.get('MAGENTA_CUDA_LIBRARIES_READY') != '1':
        current_cuda_paths = ':'.join(str(current_library_path.resolve()) for current_library_path in current_library_root.glob('*/lib'))
        current_process_result = subprocess.run([sys.executable,str(Path(__file__))],env=dict(os.environ,LD_LIBRARY_PATH=current_cuda_paths,MAGENTA_CUDA_LIBRARIES_READY='1'))
        raise SystemExit(current_process_result.returncode)
    verify_encoder_cuda()
