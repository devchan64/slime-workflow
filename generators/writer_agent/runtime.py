"""고정 모델·GPU 전용 임베딩 및 구조화된 작성 추론."""
import contextlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
from jsonschema import Draft202012Validator
from . import prepare
from .documents import parse_unique_json
from .index import normalize_embedding_vector

EMBEDDING_SERVER_PORT=8774
EMBEDDING_INPUT_LIMIT=4000
MODEL_SERVER_PORT=8773
MODEL_SERVER_ALIAS='slime-writer-local'
MODEL_CONTEXT_LIMIT=12288
MODEL_OUTPUT_LIMIT=2400
MODEL_START_TIMEOUT=120
MODEL_REQUEST_TIMEOUT=180

def request_local_model(current_endpoint_path,current_request_body=None,current_server_port=MODEL_SERVER_PORT):
    current_request_data=json.dumps(current_request_body,ensure_ascii=False).encode() if current_request_body is not None else None
    current_http_request=urllib.request.Request(f'http://127.0.0.1:{current_server_port}'+current_endpoint_path,data=current_request_data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(current_http_request,timeout=MODEL_REQUEST_TIMEOUT) as current_http_response:
        return parse_unique_json(current_http_response.read().decode())


@contextlib.contextmanager
def start_managed_server(current_run_root,current_runtime_kind='generation'):
    if current_runtime_kind not in {'generation','embedding'}:
        raise ValueError('지원하지 않는 고정 런타임')
    embedding_runtime_flag=current_runtime_kind=='embedding'
    current_server_port=EMBEDDING_SERVER_PORT if embedding_runtime_flag else MODEL_SERVER_PORT
    current_model_name=prepare.EMBEDDING_DOWNLOAD_NAME if embedding_runtime_flag else prepare.MODEL_DOWNLOAD_NAME
    current_model_digest=prepare.EMBEDDING_DOWNLOAD_SHA256 if embedding_runtime_flag else prepare.MODEL_DOWNLOAD_SHA256
    prepare.inspect_gpu_environment(1024 if embedding_runtime_flag else 4096)
    prepared_manifest_path=prepare.RUNTIME_INSTALL_ROOT/'prepared.json'
    if not prepared_manifest_path.exists():
        raise RuntimeError('모델 환경이 준비되지 않았습니다. 관리도구에서 환경 준비를 실행하세요.')
    current_manifest_data=parse_unique_json(prepared_manifest_path.read_text())
    with prepare.trace_runtime_progress('verify'):
        if prepare.calculate_file_digest(prepare.MODEL_DOWNLOAD_ROOT/current_model_name)!=current_model_digest:
            raise ValueError('모델 체크섬 불일치')
        if prepare.calculate_file_digest(prepare.RUNTIME_SERVER_PATH)!=current_manifest_data['server_binary_sha256']:
            raise ValueError('서버 바이너리 체크섬 불일치')
    with socket.socket() as port_probe_socket:
        port_probe_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        port_probe_socket.bind(('127.0.0.1',current_server_port))
    server_log_path=current_run_root/('embedding-server.log' if embedding_runtime_flag else 'model-server.log')
    server_environment_values=os.environ.copy()
    server_environment_values['LD_LIBRARY_PATH']=':'.join(current_manifest_data['runtime_library_paths'])
    server_environment_values['CUDA_VISIBLE_DEVICES']='0'
    server_command_parts=[str(prepare.RUNTIME_SERVER_PATH),'-m',str(prepare.MODEL_DOWNLOAD_ROOT/prepare.MODEL_DOWNLOAD_NAME),'--alias',MODEL_SERVER_ALIAS,'--host','127.0.0.1','--port',str(MODEL_SERVER_PORT),'-ngl','all','--fit','off','-c',str(MODEL_CONTEXT_LIMIT),'-np','1','-b','256','-ub','128','--jinja','--reasoning','off','--no-context-shift','--verbosity','4','--cors-origins','http://127.0.0.1:8769']
    if embedding_runtime_flag:
        server_command_parts=[str(prepare.RUNTIME_SERVER_PATH),'-m',str(prepare.MODEL_DOWNLOAD_ROOT/current_model_name),'--alias','slime-writer-embedding','--host','127.0.0.1','--port',str(current_server_port),'-ngl','all','--fit','off','-c','4096','-b','4096','-ub','4096','-np','1','--embedding','--pooling','last','--verbosity','4']
    prepare.emit_runtime_trace('server',f'CUDA 서버 시작: {current_runtime_kind}')
    server_log_offset=server_log_path.stat().st_size if server_log_path.exists() else 0
    with server_log_path.open('a') as server_log_stream:
        server_process_handle=subprocess.Popen(server_command_parts,stdout=server_log_stream,stderr=subprocess.STDOUT,env=server_environment_values)
        try:
            server_start_time=time.monotonic()
            with prepare.trace_runtime_progress('loading',lambda:f'로그바이트={server_log_path.stat().st_size}'):
                while True:
                    if server_process_handle.poll() is not None:
                        raise RuntimeError('모델 서버 시작 실패: '+server_log_path.read_text(errors='replace')[-2500:])
                    if time.monotonic()-server_start_time>MODEL_START_TIMEOUT:
                        raise TimeoutError('모델 적재 제한 시간 초과')
                    try:
                        current_health_data=request_local_model('/health',current_server_port=current_server_port)
                        if current_health_data.get('status')=='ok':
                            break
                    except (urllib.error.URLError,TimeoutError):
                        time.sleep(0.5)
            current_server_logs=server_log_path.read_bytes()[server_log_offset:].decode(errors='replace')
            layer_offload_match=re.search(r'offloaded (\d+)/(\d+) layers to GPU',current_server_logs)
            if not layer_offload_match or layer_offload_match.group(1)!=layer_offload_match.group(2):
                raise RuntimeError('모든 모델 레이어의 GPU 적재를 확인하지 못했습니다.')
            prepare.emit_runtime_trace('gpu',f'전체 GPU 적재 확인: {layer_offload_match.group(0)}')
            yield
        finally:
            server_process_handle.terminate()
            try:
                server_process_handle.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server_process_handle.kill()
                server_process_handle.wait()


def request_document_embedding(current_source_text):
    current_token_values=request_local_model('/tokenize',{'content':current_source_text,'add_special':True},EMBEDDING_SERVER_PORT)
    if len(current_token_values['tokens'])>EMBEDDING_INPUT_LIMIT:
        raise ValueError('임베딩 입력 토큰 예산 초과: 원문을 자동 절단하지 않습니다.')
    current_response_values=request_local_model('/v1/embeddings',{'model':'slime-writer-embedding','input':current_source_text,'encoding_format':'float'},EMBEDDING_SERVER_PORT)
    if not isinstance(current_response_values.get('data'),list) or len(current_response_values['data'])!=1 or current_response_values['data'][0].get('index')!=0:
        raise ValueError('임베딩 API 응답 계약 위반')
    return normalize_embedding_vector(current_response_values['data'][0]['embedding'])


def request_structured_result(current_system_text,current_request_values,current_output_schema,current_output_limit=MODEL_OUTPUT_LIMIT):
    current_messages=[{'role':'system','content':current_system_text},{'role':'user','content':json.dumps(current_request_values,ensure_ascii=False)}]
    current_prompt_values=request_local_model('/apply-template',{'messages':current_messages,'add_generation_prompt':True})
    current_token_values=request_local_model('/tokenize',{'content':current_prompt_values['prompt'],'add_special':False})
    if len(current_token_values['tokens'])+current_output_limit>MODEL_CONTEXT_LIMIT:
        raise ValueError('관련 원문이 모델 입력 예산을 초과했습니다. 지시 범위를 좁혀 주세요. 원문은 자동 절단하지 않습니다.')
    current_response_values=request_local_model('/v1/chat/completions',{'model':MODEL_SERVER_ALIAS,'messages':current_messages,'temperature':0.1,'max_tokens':current_output_limit,'response_format':{'type':'json_schema','json_schema':{'name':'writer_proposal','strict':True,'schema':current_output_schema}}})
    if len(current_response_values.get('choices',[]))!=1 or current_response_values['choices'][0]['finish_reason']!='stop':raise ValueError('모델 출력 미완료 또는 응답 계약 오류')
    current_result_values=parse_unique_json(current_response_values['choices'][0]['message']['content'])
    Draft202012Validator(current_output_schema).validate(current_result_values)
    return current_result_values
