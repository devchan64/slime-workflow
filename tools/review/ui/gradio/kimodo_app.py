"""Kimodo NF4 실험 폼. 실행과 기록 수명은 공용 게이트웨이가 담당한다."""
import json
import gradio as gr
import yaml
import base64
from pathlib import Path
from tools.review.common.gradio_input_preview import build_input_preview
from generators.kimodo.contracts import KIMODO_JOB_STORAGE, KIMODO_MAXIMUM_SEED_VALUE
from generators.kimodo.contracts import KIMODO_CONFIG_ROOT, UniqueConfigLoader, KIMODO_DIRECTION_RECORDS
from tools.review.common.gradio_identifiers import build_generation_identifier
from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS,normalize_kimodo_prompt,validate_kimodo_request
from tools.review.common.management_client import execute_remote_management_command
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.gradio_button_guidance import build_button_guidance
from tools.review.common.gradio_seed import build_generation_seed
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.gradio_video_results import build_video_job_monitor,render_video_generation_result
from tools.review.common.generation_cleanup import GENERATION_CLEANUP_SCOPE_TEXT


KIMODO_INPUT_MINIMUM_WIDTH = 320
KIMODO_POSE_PREVIEW_WIDTH = 240
KIMODO_POSE_PREVIEW_HEIGHT = 160

def load_proportion_examples():
    current_workspace_root=Path(__file__).resolve().parents[4]
    current_config_record=yaml.load((KIMODO_CONFIG_ROOT/'proportion-examples.yaml').read_text(),Loader=UniqueConfigLoader)
    if not isinstance(current_config_record,dict) or set(current_config_record)!={'schema_version','examples'} or current_config_record['schema_version']!=1 or not isinstance(current_config_record['examples'],list):
        raise ValueError('신체 비율 예제 목록 계약 오류')
    current_example_mapping={}
    for current_example_record in current_config_record['examples']:
        if not isinstance(current_example_record,dict) or set(current_example_record)!={'id','label','images'} or any(not isinstance(current_example_record[current_field_name],str) or not current_example_record[current_field_name].strip() for current_field_name in ('id','label')):
            raise ValueError('신체 비율 예제 필드 오류')
        if current_example_record['id'] in current_example_mapping:
            raise ValueError('신체 비율 예제 ID 중복')
        current_image_paths=current_example_record['images']
        if not isinstance(current_image_paths,list) or not 1<=len(current_image_paths)<=8:
            raise ValueError('신체 비율 예제는 이미지 1~8장이 필요합니다.')
        current_resolved_paths=[]
        for current_image_path in current_image_paths:
            if not isinstance(current_image_path,str):
                raise ValueError('신체 비율 예제 경로는 문자열이어야 합니다.')
            current_resolved_path=(current_workspace_root/current_image_path).resolve()
            if not any(current_resolved_path.is_relative_to(current_workspace_root/current_allowed_directory) for current_allowed_directory in ('assets','baseline')) or not current_resolved_path.is_file():
                raise ValueError(f'신체 비율 예제 이미지 경로 오류: {current_image_path}')
            current_resolved_paths.append(str(current_resolved_path))
        current_example_mapping[current_example_record['id']]={'label':current_example_record['label'],'images':current_resolved_paths}
    return current_example_mapping


def apply_proportion_example(current_example_identifier):
    current_example_mapping=load_proportion_examples()
    if current_example_identifier not in current_example_mapping:
        raise ValueError('신체 비율 예제를 선택하세요.')
    return True,current_example_mapping[current_example_identifier]['images']


def execute_kimodo_command(current_command_name,current_payload_record):
    return execute_remote_management_command('kimodo',current_command_name,current_payload_record)


def build_kimodo_payload(current_prompt_text,current_frame_count,current_step_count,current_seed_value,current_guidance_value,current_heading_value,current_postprocessing_value,current_direction_names=None,current_horizontal_removal=False,current_proportions_enabled=False,current_reference_paths=None,current_scale_percent=KIMODO_DEFAULT_SETTINGS['openpose_scale_percent'],current_include_hands=False,current_include_face=False,current_segment_text="",current_endpoint_identifier=None,current_keyframe_rows=None,current_elevation_angle=0):
    for current_integer_value in (current_frame_count,current_step_count,current_seed_value):
        if type(current_integer_value) not in (int,float) or not float(current_integer_value).is_integer():
            raise ValueError('프레임·스텝·시드는 정수로 입력하세요.')
    current_request_record = {'pose_include_hands':current_include_hands,'pose_include_face':current_include_face,'openpose_scale_percent':current_scale_percent,'remove_horizontal_motion':current_horizontal_removal,'action':'generate','prompt':current_prompt_text,'frames':int(current_frame_count),'steps':int(current_step_count),'seed':int(current_seed_value),'guidance_scale':current_guidance_value,'heading_degrees':current_heading_value,'post_processing':current_postprocessing_value,'directions':list(KIMODO_DEFAULT_SETTINGS['directions']) if current_direction_names is None else current_direction_names}
    if current_elevation_angle != 0:
        current_request_record['camera_elevation_degrees']=current_elevation_angle
    if current_endpoint_identifier:
        current_request_record['endpoint_pose_id']=current_endpoint_identifier
    if current_keyframe_rows:
        current_request_record['keyframes'] = [{'id':current_row_value[0],'frame':current_row_value[1]} for current_row_value in current_keyframe_rows]
    if current_segment_text.strip():
        current_frame_tokens=current_segment_text.split()
        if any(not current_frame_token.isdigit() for current_frame_token in current_frame_tokens):
            raise ValueError('구간 프레임은 공백으로 구분한 정수로 입력하세요.')
        current_request_record['segment_frames']=[int(current_frame_token) for current_frame_token in current_frame_tokens]
    if current_reference_paths and not current_proportions_enabled:
        raise ValueError('신체 비율 참조 이미지가 있지만 비율 적용이 꺼져 있습니다. 적용을 켜거나 참조 이미지를 제거하세요. 참조를 무시한 채 생성하지 않습니다.')
    if current_proportions_enabled:
        if not current_reference_paths:
            raise ValueError('신체 비율 맞춤을 켰다면 참조 이미지를 첨부하세요.')
        current_request_record['proportion_images']=[base64.b64encode(Path(current_reference_path).read_bytes()).decode() for current_reference_path in current_reference_paths]
    current_validated_request=validate_kimodo_request(current_request_record)
    if current_proportions_enabled:
        current_request_record['proportion_images']=current_validated_request['images']
    return current_request_record


def describe_kimodo_prompt(current_prompt_text,current_segment_text=""):
    if not current_prompt_text or not current_prompt_text.strip():
        return '원문 0단어 · 최종 0단어'
    try:
        current_final_prompt = "\n".join(normalize_kimodo_prompt(current_prompt_line) for current_prompt_line in current_prompt_text.splitlines() if current_prompt_line.strip()) if current_segment_text.strip() else normalize_kimodo_prompt(current_prompt_text)
        return f'원문 {len(current_prompt_text.split())}단어 · 최종 {len(current_final_prompt.split())}단어 · 공식 공백·대소문자·문장부호 정규화\n\n최종 입력: {current_final_prompt}'
    except (OSError,ValueError) as current_prompt_error:
        return f'원문 {len(current_prompt_text.split())}단어 · 최종 확인 불가: {current_prompt_error}'


def restore_kimodo_inputs(current_history_record):
    current_request_record = current_history_record['request']
    if current_request_record.get('action')=='reference-analysis':
        current_request_record={**KIMODO_DEFAULT_SETTINGS,**current_request_record,'prompt':'','directions':list(KIMODO_DEFAULT_SETTINGS['directions'])}
    current_reference_paths=[]
    current_job_root=(KIMODO_JOB_STORAGE/current_history_record['id']).resolve()
    if current_job_root.parent!=KIMODO_JOB_STORAGE.resolve():
        raise ValueError('Kimodo 이력 경로 오류')
    for current_reference_name in current_request_record.get('references',[]):
        current_reference_path=(current_job_root/current_reference_name).resolve()
        if current_reference_path.parent!=current_job_root or not current_reference_path.is_file():
            raise ValueError('신체 비율 참조 사본 누락 또는 경로 오류')
        current_reference_paths.append(str(current_reference_path))
    current_keyframe_placements=current_request_record.get('keyframes',[])
    if current_request_record.get('endpoint_pose_id'):
        if current_request_record['endpoint_pose_id']!='relaxed-standing-v1' or current_keyframe_placements:
            raise ValueError('이전 양 끝 자세를 키프레임으로 변환할 수 없습니다.')
        current_keyframe_placements=[{'id':'b0000000000000000000000000000004','frame':1},{'id':'b0000000000000000000000000000004','frame':current_request_record['frames']}]
    return tuple(current_request_record[current_field_name] for current_field_name in ('prompt','frames','steps','seed','guidance_scale','heading_degrees','post_processing'))+(current_request_record.get('directions',['front_left']),current_request_record.get('remove_horizontal_motion',False),bool(current_reference_paths),current_reference_paths,current_request_record.get('openpose_scale_percent',100.0),current_request_record.get('pose_include_hands',False),current_request_record.get('pose_include_face',False),' '.join(map(str,current_request_record.get('segment_frames',[]))),None,[[current_placement['id'],current_placement['frame']] for current_placement in current_keyframe_placements],current_request_record.get('camera_elevation_degrees',0),current_history_record['id'])


def check_kimodo_readiness(current_model_ready,current_prompt_text,current_direction_names,current_proportions_enabled=False,current_reference_paths=None,current_keyframe_rows=None,current_postprocessing_enabled=False,current_segment_text='',current_endpoint_identifier=None,current_horizontal_removal=False):
    current_keyframe_compatible = not current_keyframe_rows or (current_postprocessing_enabled and not current_endpoint_identifier and not current_horizontal_removal)
    return bool(current_model_ready and current_prompt_text and current_prompt_text.strip() and current_direction_names and (bool(current_proportions_enabled)==bool(current_reference_paths)) and current_keyframe_compatible)


def load_kimodo_examples():
    current_example_record = yaml.load((KIMODO_CONFIG_ROOT/'prompt-examples.yaml').read_text(), Loader=UniqueConfigLoader)
    if not isinstance(current_example_record,dict) or set(current_example_record)!={'schema_version','examples'} or current_example_record['schema_version']!=1 or not isinstance(current_example_record['examples'],list) or not current_example_record['examples']:
        raise ValueError('Kimodo 프롬프트 예시 계약 오류')
    current_example_mapping = {}
    for current_example_value in current_example_record['examples']:
        if not isinstance(current_example_value,dict) or set(current_example_value)-{'reference_example'} not in ({'id','label','prompt','frames'},{'id','label','prompt','frames','settings'}) or any(not isinstance(current_example_value[current_field_name],str) or not current_example_value[current_field_name].strip() for current_field_name in ('id','label','prompt')):
            raise ValueError('Kimodo 예시 필드 오류')
        if current_example_value['id'] in current_example_mapping:
            raise ValueError('Kimodo 예시 ID 중복')
        build_kimodo_payload(current_example_value['prompt'],current_example_value['frames'],KIMODO_DEFAULT_SETTINGS['steps'],KIMODO_DEFAULT_SETTINGS['seed'],KIMODO_DEFAULT_SETTINGS['guidance_scale'],KIMODO_DEFAULT_SETTINGS['heading_degrees'],KIMODO_DEFAULT_SETTINGS['post_processing'])
        if 'settings' in current_example_value:
            current_settings_record = current_example_value['settings']
            if not isinstance(current_settings_record,dict) or set(current_settings_record)-{'segment_frames','openpose_scale_percent','pose_include_hands','pose_include_face','keyframes','camera_elevation_degrees'}!={'steps','seed','guidance_scale','heading_degrees','post_processing','directions','remove_horizontal_motion'}:
                raise ValueError('Kimodo 예시 설정 필드 오류')
            validate_kimodo_request({'action':'generate','prompt':current_example_value['prompt'],'frames':current_example_value['frames'],**current_settings_record})
        if 'reference_example' in current_example_value and current_example_value['reference_example'] not in load_proportion_examples():
            raise ValueError('등록되지 않은 신체 비율 참조 예제')
        current_example_mapping[current_example_value['id']] = current_example_value
    return current_example_mapping


def apply_kimodo_example(current_example_identifier):
    current_example_mapping = load_kimodo_examples()
    if current_example_identifier not in current_example_mapping:
        raise ValueError('불러올 동작 예시를 선택하세요.')
    current_example_record = current_example_mapping[current_example_identifier]
    current_settings_record = current_example_record.get('settings',{})
    return (current_example_record['prompt'],current_example_record['frames'])+tuple(current_settings_record[current_field_name] if current_field_name in current_settings_record else gr.skip() for current_field_name in ('steps','seed','guidance_scale','heading_degrees','post_processing','directions','remove_horizontal_motion'))


def apply_complete_kimodo_example(current_example_identifier):
    current_example_mapping=load_kimodo_examples()
    if current_example_identifier not in current_example_mapping:
        raise gr.Error('먼저 동작 예시를 선택하세요.')
    current_example_record=current_example_mapping[current_example_identifier]
    current_settings_record=current_example_record.get('settings',{})
    current_reference_identifier=current_example_record.get('reference_example')
    current_reference_values=apply_proportion_example(current_reference_identifier) if current_reference_identifier else (False,[])
    current_keyframe_rows = [[current_item['id'],current_item['frame']] for current_item in current_settings_record.get('keyframes',[])]
    return (*apply_kimodo_example(current_example_identifier),*current_reference_values,*(current_settings_record.get(current_field_name,gr.skip()) for current_field_name in ('openpose_scale_percent','pose_include_hands','pose_include_face')),' '.join(map(str,current_settings_record.get('segment_frames',[]))),None,current_keyframe_rows,current_settings_record.get('camera_elevation_degrees',0))


def describe_kimodo_duration(current_frame_count):
    if type(current_frame_count) not in (int,float) or not 30<=current_frame_count<=300 or not float(current_frame_count).is_integer():
        return '프레임 수를 30~300 사이의 정수로 입력하세요.'
    return f'모션 길이 **{current_frame_count/30:g}초** · {int(current_frame_count)}프레임 · 30fps'


def describe_kimodo_input_summary(current_proportions_enabled,current_reference_paths,current_keyframe_rows,current_postprocessing_enabled,current_horizontal_removal):
    """접힌 설정을 열지 않아도 생성에 적용되는 상태를 확인한다."""
    current_reference_count = len(current_reference_paths or [])
    if current_proportions_enabled and current_reference_count:
        current_reference_text = f'적용 · {current_reference_count}장'
    elif current_proportions_enabled or current_reference_count:
        current_reference_text = '설정 확인 필요'
    else:
        current_reference_text = '꺼짐'
    return (f"**현재 설정** · 신체 비율: {current_reference_text} · 키프레임: {len(current_keyframe_rows or [])}개"
            f" · 공식 후처리: {'켜짐' if current_postprocessing_enabled else '꺼짐'}"
            f" · 수평 이동 제거: {'켜짐' if current_horizontal_removal else '꺼짐'}")


def render_kimodo_result(current_job_identifier,current_status_record,current_server_address):
    import html
    if current_status_record.get('reference_analysis_only'):
        return '<p>참조 신체 비율 추출 검증 · 모션 생성 아님. 추출 포즈 '+str(int(current_status_record.get('reference_observation_count',0)))+'개. 영상은 검출 인물별 포즈를 순서대로 보여줍니다. ZIP에 원시 점수·채택 근거·최종 비율을 포함합니다.</p>'+render_video_generation_result(current_job_identifier,current_status_record,current_server_address)
    if current_status_record.get('preprocess_videos'):
        from tools.review.common.gradio_video_results import render_condition_video_previews
        current_pose_status_html='<p>직접 포즈: '+('생성 완료' if current_status_record.get('direct_pose_status')=='completed' else '결과 기록 없음')+'</p>'
        if current_status_record.get('dwpose_status')=='warning':
            current_pose_status_html+='<p><strong>DWPose: 생성 오류 · 경고</strong> — '+html.escape(current_status_record.get('dwpose_error','상세 원인은 실행 로그를 확인하세요.'))+'<br>직접 포즈는 사용할 수 있으며 전체 모션 작업은 완료됐습니다.</p>'
        else:
            current_pose_status_html+='<p>DWPose: '+('생성 완료' if current_status_record.get('dwpose_status')=='completed' else '결과 기록 없음')+'</p>'
        return current_pose_status_html+'<p>SOMA 렌더: 원본 동작 검수 · 직접 포즈: SOMA 관절 투영 · DWPose: 렌더에서 검출한 포즈. Fun Control에 입력할 때 30fps 영상은 16fps로 변환하세요. 참조 비율은 포즈 출력에 적용하며 SOMA 원본은 유지합니다.</p><p><a href="#kimodo-history-keyframe-save">선택한 이력의 키프레임 저장 영역으로 이동</a></p>'+render_condition_video_previews(current_status_record)+'<p>전체 미리보기와 다운로드</p>'+render_video_generation_result(current_job_identifier,current_status_record,current_server_address)
    current_comparison_url = current_status_record.get('comparison_video')
    if not current_comparison_url:
        return render_video_generation_result(current_job_identifier,current_status_record,current_server_address)+'<p>이 결과에는 오픈포즈 비교 영상이 없습니다.</p>'
    current_comparison_html = render_video_generation_result(current_job_identifier,{**current_status_record,'video':current_comparison_url},current_server_address)
    current_pose_description = 'SOMA 원본(정면·측면) → SOMA 직접 투영 오픈포즈. 같은 프레임을 재생하며 카메라 높이·배율은 서로 다릅니다. 오픈포즈는 리타게팅 전 몸 관절이며 실제 눈 관절을 포함합니다. 코·귀는 대응 관절이 없어 생략하며 손 상세 점은 없습니다.' if current_status_record.get('pose_source')=='soma' else '이전 비교 결과: 오픈포즈는 리타게팅 후 ANNY 관절 투영입니다. SOMA 원본 패널은 결과에 따라 없을 수 있습니다.'
    if current_status_record.get('remove_horizontal_motion'):
        current_pose_description = '수평 이동 제거 적용: SOMA·오픈포즈는 보정본입니다. 원본 motion.npz와 보정 motion-in-place.npz는 ZIP에 포함됩니다.'
    if current_status_record.get('pose_schema')=='soma-body18-v2':
        current_pose_description += ' 이 과거 결과는 v2이며 Head를 코로 사용한 대리점이 포함됩니다. 신규 v3에서는 제거했습니다.'
    if current_status_record.get('reference_proportions'):
        current_pose_description += f" 참조 추출 포즈: {int(current_status_record.get('reference_observation_count',0))}개."
        current_pose_description += ' 참조 신체 비율 보정 적용: OpenPose의 너비·팔다리 길이만 조정했습니다. SOMA 원본과 체형이 다릅니다. ZIP의 reference-proportions.json에서 채택 관측·비율과 추출 포즈를 확인하세요.'
    current_pose_description += f" OpenPose 출력 크기: {current_status_record.get('openpose_scale_percent',100.0):g}%."
    return '<p>'+current_pose_description+'</p>'+current_comparison_html+f'<p><a href="{html.escape(current_status_record["video"],quote=True)}" target="_blank">SOMA MP4</a></p>'


def build_kimodo_interface(current_server_address,current_command_callback=None):
    current_execute_command = current_command_callback or execute_kimodo_command
    with gr.Blocks(title='Kimodo 모션 생성기') as current_interface_blocks:
        gr.Markdown('## Kimodo 모션 생성기 · NF4 실험\n텍스트로 SOMA 모션을 생성한 뒤 이 생성기에서 VideoX-Fun DWPose 검출과 선택 참조 관절 길이 보정을 수행합니다. Fun Control 입력에는 결과 포즈 영상을 16fps로 변환하세요. SOMA 렌더는 검수용입니다.')
        with gr.Accordion('고정 설정 · 모델 준비',open=False):
            gr.Markdown('고정: Kimodo-SOMA-RP-v1.2 · 모션 FP32 · LLM2Vec Llama 3 8B NF4 / BF16 연산 · CUDA · 30fps · 1개 샘플 · DDIM. 인코딩 후 인코더를 해제하고 모션을 생성합니다. 이후 모션 모델을 해제하고 SOMA 몸 관절을 512×512·30fps 정사영 포즈로 변환합니다. 모델 선택·부정 프롬프트는 제공하지 않습니다. 선택 이미지 참조는 모션 모델 입력이 아니라 OpenPose 출력 비율 보정에 사용합니다.')
        current_model_ready = gr.State(False)
        current_model_output = gr.Markdown('모델 상태 확인 중')
        current_refresh_button = gr.Button('모델 준비 상태 확인')
        def refresh_kimodo_assets():
            try:
                current_asset_record = current_execute_command('model-status',{})
                return current_asset_record['message'],current_asset_record['ready']
            except Exception as current_asset_error:
                return f'모델 상태 확인 실패: {current_asset_error}',False
        current_refresh_event = current_refresh_button.click(refresh_kimodo_assets,outputs=[current_model_output,current_model_ready],queue=False)
        current_load_event = current_interface_blocks.load(refresh_kimodo_assets,outputs=[current_model_output,current_model_ready])
        gr.Markdown('### 모션 설정')
        current_example_mapping = load_kimodo_examples()
        with gr.Row():
            current_example_selector = gr.Dropdown(choices=[(f"{current_example_record['label']} · 신체 비율 보정 {'켜짐' if current_example_record.get('reference_example') else '꺼짐'}",current_example_name) for current_example_name,current_example_record in current_example_mapping.items()],value=None,label='동작 예시',info='예제를 선택하고 불러오기를 눌러야 입력에 적용됩니다. 자동 생성하지 않습니다.')
            current_example_button = gr.Button('예시 불러오기')
        with gr.Row():
            with gr.Column(min_width=KIMODO_INPUT_MINIMUM_WIDTH):
                current_prompt_control = gr.Textbox(label='동작 프롬프트',value=KIMODO_DEFAULT_SETTINGS['prompt'],lines=3,info='영문으로 주체와 신체 동작을 간결하게 작성하세요. 카메라·외형 묘사보다 실제 행동을 지정하세요. 100단어·400토큰 이내. 순차 생성은 줄마다 독립된 동작 설명을 쓰고 아래 구간 프레임을 지정하세요. 각 설명은 A person으로 시작하고 1~2개 동작에 집중하세요.')
            with gr.Column(min_width=KIMODO_INPUT_MINIMUM_WIDTH):
                current_direction_control = gr.CheckboxGroup(choices=[(f"{current_direction_record['label']} ({current_direction_record['angle']}°)",current_direction_name) for current_direction_name,current_direction_record in KIMODO_DIRECTION_RECORDS.items()],value=KIMODO_DEFAULT_SETTINGS['directions'],label='출력 방향 · 복수 선택',info='카메라 방향입니다. 동작 프롬프트·초기 방향은 변경하지 않습니다. 여러 방향은 같은 프레임으로 비교하며 렌더 시간·저장 용량이 늘어납니다.')
        current_elevation_control = gr.Radio(choices=[('수평 0°',0),('위에서 15°',15),('위에서 30°',30)],value=0,label='카메라 고도',info='양의 고도는 위에서 내려다보는 각도입니다. 모션 자체는 회전하지 않습니다.')
        current_prompt_summary = gr.Markdown(describe_kimodo_prompt(KIMODO_DEFAULT_SETTINGS['prompt']))
        current_frame_control = gr.Number(label='프레임 수',value=KIMODO_DEFAULT_SETTINGS['frames'],minimum=30,maximum=300,precision=0,info='30fps: 90프레임=3초, 150프레임=5초, 300프레임=10초. 8GB의 모든 길이를 보장하지 않습니다.')
        current_duration_output = gr.Markdown(describe_kimodo_duration(KIMODO_DEFAULT_SETTINGS['frames']))
        current_frame_control.change(describe_kimodo_duration,current_frame_control,current_duration_output,queue=False)
        current_segment_control = gr.Textbox(label='순차 생성 구간 프레임 · 선택',value='',info='예: 90 120 90. 프롬프트 3줄에 각각 적용하며 합계는 전체 프레임 수와 같아야 합니다. 비우면 단일 설명입니다. 공식 multi_prompt 순차 생성과 기본 5프레임 전환을 사용합니다. 구간마다 설정한 스텝을 실행합니다.')
        current_seed_control = build_generation_seed(default_seed_value=KIMODO_DEFAULT_SETTINGS['seed'], maximum_seed_value=KIMODO_MAXIMUM_SEED_VALUE)
        with gr.Accordion('고급 설정',open=False):
            current_steps_control = gr.Number(label='샘플링 스텝',value=KIMODO_DEFAULT_SETTINGS['steps'],minimum=2,maximum=100,precision=0,info='공식 기본 100. 2스텝은 실행 연결 확인용이며 품질 평가에 사용하지 마세요.')
            current_guidance_control = gr.Number(label='텍스트 CFG',value=KIMODO_DEFAULT_SETTINGS['guidance_scale'],minimum=0,maximum=10,info='공식 기본 2. 텍스트 조건의 영향이며 원하는 동작의 성공을 보장하지 않습니다.')
            current_heading_control = gr.State(value=KIMODO_DEFAULT_SETTINGS['heading_degrees'])
            current_postprocessing_control = gr.Checkbox(label='공식 발 미끄러짐 후처리',value=KIMODO_DEFAULT_SETTINGS['post_processing'],info='기본 해제: 원본 동작 비교. 활성화하면 공식 후처리를 적용하고 실행 기록에 남깁니다.')
            gr.Markdown('[공식 모델카드](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2) · [NF4 인코더](https://huggingface.co/matbee/kimodo-llm2vec-nf4)\n\nANNY 리그 기능은 폐기되었습니다. SOMA 몸 포즈에는 실제 눈 관절이 포함됩니다. 코·귀는 대응 관절이 없어 생략하며 손 상세 점은 없습니다.\n\nNF4는 커뮤니티 양자화본입니다. BF16과 동작이 달라질 수 있으며 실제 품질은 결과를 검수하세요. 내부 30관절 추론을 공식 API가 77관절로 확장해 저장합니다.')
        current_endpoint_selector = gr.State(None)
        with gr.Accordion('저장한 키프레임 배치 · 선택',open=False):
            gr.Markdown('저장 목록을 새로고침하고 키프레임과 출력 프레임 번호를 골라 추가하세요. 1은 시작, 전체 프레임 수는 종료입니다. 공식 발 미끄러짐 후처리를 켜고 수평 이동 제거를 꺼야 하며 같은 출력 번호는 한 번만 지정합니다.')
            current_keyframe_refresh = gr.Button('저장 목록 새로고침')
            current_keyframe_selector = gr.Dropdown(choices=[],label='저장한 키프레임')
            current_keyframe_saved_preview = gr.Image(label='저장한 자세 미리보기',interactive=False,buttons=[])
            current_keyframe_target = gr.Number(label='배치할 출력 프레임 번호 · 1부터 시작',value=1,minimum=1,precision=0)
            with gr.Row():
                current_keyframe_add = gr.Button('배치 추가')
                current_keyframe_add_endpoints = gr.Button('선택 자세를 시작·종료에 배치')
                current_keyframe_remove = gr.Button('입력한 프레임 배치 삭제')
                current_keyframe_clear = gr.Button('배치 모두 지우기')
            current_keyframe_rows = gr.State([])
            current_keyframe_display = gr.Dataframe(headers=['키프레임 ID','출력 프레임'],datatype=['str','number'],interactive=False,label='현재 배치',value=[])
            current_keyframe_notice = gr.Markdown('배치 없음 · 목록을 새로고침해 키프레임을 선택하세요.')
            gr.Markdown('**저장 목록 관리** · 배치와 별도로 기존 항목을 교체하거나 폐기합니다.')
            with gr.Accordion('키프레임 교체',open=False):
                gr.Markdown('교체할 이전 항목과 새 항목을 선택하세요. 이전 항목은 목록에서 제외하고 보관하며, 기존 작업의 입력 사본은 유지됩니다. 아래 확인은 인라인 확인 영역입니다.')
                current_replace_old = gr.Dropdown(choices=[],label='목록에서 제외할 기존 키프레임')
                current_replace_new = gr.Dropdown(choices=[],label='사용할 새 키프레임')
                current_replace_prepare = gr.Button('교체 내용 확인')
                current_replace_state = gr.State(None)
                current_replace_message = gr.Markdown('두 항목을 선택하고 교체 내용을 확인하세요.')
                with gr.Row():
                    current_replace_confirm = gr.Button('교체 확인',interactive=False)
                    current_replace_cancel = gr.Button('취소',interactive=False)
            with gr.Accordion('사용자 키프레임 폐기',open=False):
                gr.Markdown('선택한 사용자 키프레임을 목록에서 제외하고 별도 보관합니다. 생성 작업의 입력 사본과 제작 기준 예제는 유지됩니다. 아래는 인라인 확인 영역입니다.')
                current_retire_selector=gr.Dropdown(choices=[],multiselect=True,label='폐기할 사용자 키프레임')
                current_retire_prepare=gr.Button('폐기 내용 확인',interactive=False)
                current_retire_state=gr.State(None)
                current_retire_message=gr.Markdown('저장 목록을 새로고침하고 폐기할 항목을 선택하세요.')
                with gr.Row():
                    current_retire_confirm=gr.Button('폐기 확인',interactive=False)
                    current_retire_cancel=gr.Button('폐기 취소',interactive=False)
            def refresh_retire_choices():
                from tools.review.domains.kimodo.keyframe_storage import KIMODO_EXAMPLE_KEYFRAME_IDENTIFIERS
                current_records=current_execute_command('keyframe-list',{})['records']
                current_choices=[(f"{current_record['tag']} · {current_record['source_job']} · {current_record['source_frame']}프레임 · {current_record['id'][:8]}",current_record['id']) for current_record in current_records if current_record['id'] not in KIMODO_EXAMPLE_KEYFRAME_IDENTIFIERS]
                return gr.update(choices=current_choices,value=[])
            def prepare_keyframe_retirement(current_identifiers):
                if not current_identifiers:
                    raise gr.Error('폐기할 사용자 키프레임을 선택하세요.')
                return list(current_identifiers),'다음 항목을 목록에서 제외하고 보관합니다: '+', '.join(current_identifiers),gr.update(interactive=True),gr.update(interactive=True)
            def confirm_keyframe_retirement(current_pending_identifiers,current_selected_identifiers):
                if not current_pending_identifiers or current_pending_identifiers!=current_selected_identifiers:
                    raise gr.Error('선택이 변경되었습니다. 폐기 내용을 다시 확인하세요.')
                current_response=current_execute_command('keyframe-retire',{'ids':current_pending_identifiers})
                return None,f"{current_response['retired_count']}개 폐기 완료. 저장 목록을 새로고침하세요.",gr.update(interactive=False),gr.update(interactive=False)
            current_keyframe_refresh.click(refresh_retire_choices,None,current_retire_selector,queue=False)
            current_retire_selector.change(lambda current_identifiers:(gr.update(interactive=bool(current_identifiers)),None,'항목을 선택한 뒤 폐기 내용을 확인하세요.',gr.update(interactive=False),gr.update(interactive=False)),current_retire_selector,[current_retire_prepare,current_retire_state,current_retire_message,current_retire_confirm,current_retire_cancel],queue=False)
            current_retire_prepare.click(prepare_keyframe_retirement,current_retire_selector,[current_retire_state,current_retire_message,current_retire_confirm,current_retire_cancel])
            current_retire_confirm.click(confirm_keyframe_retirement,[current_retire_state,current_retire_selector],[current_retire_state,current_retire_message,current_retire_confirm,current_retire_cancel])
            current_retire_cancel.click(lambda:(None,'폐기를 취소했습니다.',gr.update(interactive=False),gr.update(interactive=False)),None,[current_retire_state,current_retire_message,current_retire_confirm,current_retire_cancel])
            def refresh_replace_choices():
                current_records = current_execute_command('keyframe-list',{})['records']
                current_choices = [(f"{current_record['tag']} · {current_record['source_job']} · {current_record['source_frame']}프레임 · {current_record['id'][:8]}",current_record['id']) for current_record in current_records]
                return gr.update(choices=current_choices,value=None),gr.update(choices=current_choices,value=None)
            def prepare_keyframe_replacement(current_old_identifier,current_new_identifier):
                if not current_old_identifier or not current_new_identifier or current_old_identifier == current_new_identifier:
                    raise gr.Error('서로 다른 두 키프레임을 선택하세요.')
                return {'old_id':current_old_identifier,'new_id':current_new_identifier},f'기존 {current_old_identifier}을 목록에서 제외하고 {current_new_identifier}을 사용합니다.',gr.update(interactive=True),gr.update(interactive=True)
            def confirm_keyframe_replacement(current_pending_record,current_old_identifier,current_new_identifier):
                if current_pending_record != {'old_id':current_old_identifier,'new_id':current_new_identifier}:
                    raise gr.Error('선택이 변경되었습니다. 교체 내용을 다시 확인하세요.')
                current_execute_command('keyframe-replace',current_pending_record)
                return None,'교체 완료. 저장 목록을 새로고침하세요.',gr.update(interactive=False),gr.update(interactive=False)
            current_keyframe_refresh.click(refresh_replace_choices,None,[current_replace_old,current_replace_new],queue=False)
            current_replace_prepare.click(prepare_keyframe_replacement,[current_replace_old,current_replace_new],[current_replace_state,current_replace_message,current_replace_confirm,current_replace_cancel])
            current_replace_confirm.click(confirm_keyframe_replacement,[current_replace_state,current_replace_old,current_replace_new],[current_replace_state,current_replace_message,current_replace_confirm,current_replace_cancel])
            current_replace_cancel.click(lambda:(None,'교체를 취소했습니다.',gr.update(interactive=False),gr.update(interactive=False)),None,[current_replace_state,current_replace_message,current_replace_confirm,current_replace_cancel])
            def refresh_keyframe_choices():
                current_records = current_execute_command('keyframe-list',{})['records']
                return gr.update(choices=[(f"{current_record['tag']} · {current_record['source_job']} · {current_record['source_frame']}프레임 · {current_record['id'][:8]}",current_record['id']) for current_record in current_records],value=None)
            def preview_saved_keyframe(current_identifier):
                if not current_identifier:
                    return None
                from PIL import Image
                import io
                current_preview_record=current_execute_command('keyframe-preview',{'id':current_identifier})
                with Image.open(io.BytesIO(base64.b64decode(current_preview_record['image_base64'],validate=True))) as current_preview_image:
                    return current_preview_image.copy()
            def append_keyframe_placement(current_rows,current_identifier,current_target_number,current_total_frames,current_segment_text,current_endpoint_identifier):
                if not current_identifier or type(current_target_number) not in (int,float) or not float(current_target_number).is_integer():
                    raise gr.Error('키프레임과 정수 프레임 번호를 선택하세요.')
                if type(current_total_frames) not in (int,float) or not float(current_total_frames).is_integer() or current_total_frames < 1:
                    raise gr.Error('전체 프레임 수를 양의 정수로 입력하세요.')
                if current_endpoint_identifier:
                    raise gr.Error('키프레임을 추가하려면 양 끝 기준 자세 선택을 해제하세요.')
                current_new_rows = [*current_rows,[current_identifier,int(current_target_number)]]
                from tools.review.domains.kimodo.keyframe_storage import validate_kimodo_keyframe_placements
                current_validated_rows = validate_kimodo_keyframe_placements([{'id':current_row[0],'frame':current_row[1]} for current_row in current_new_rows],int(current_total_frames))
                current_new_rows = [[current_item['id'],current_item['frame']] for current_item in current_validated_rows]
                return current_new_rows,current_new_rows,f'{len(current_new_rows)}개 키프레임 배치됨 · 공식 후처리 켜짐',True
            current_keyframe_refresh.click(refresh_keyframe_choices,None,current_keyframe_selector,queue=False)
            current_keyframe_selector.change(preview_saved_keyframe,current_keyframe_selector,current_keyframe_saved_preview,queue=False)
            current_keyframe_add.click(append_keyframe_placement,[current_keyframe_rows,current_keyframe_selector,current_keyframe_target,current_frame_control,current_segment_control,current_endpoint_selector],[current_keyframe_rows,current_keyframe_display,current_keyframe_notice,current_postprocessing_control])
            def append_keyframe_endpoints(current_rows,current_identifier,current_total_frames):
                if not current_identifier or type(current_total_frames) not in (int,float) or not float(current_total_frames).is_integer() or current_total_frames < 30:
                    raise gr.Error('키프레임을 선택하고 전체 프레임 수를 30 이상의 정수로 입력하세요.')
                from tools.review.domains.kimodo.keyframe_storage import validate_kimodo_keyframe_placements
                current_proposed_rows=[*current_rows,[current_identifier,1],[current_identifier,int(current_total_frames)]]
                try:
                    current_placements=validate_kimodo_keyframe_placements([{'id':current_row[0],'frame':current_row[1]} for current_row in current_proposed_rows],int(current_total_frames))
                except ValueError as current_placement_error:
                    raise gr.Error(f'시작·종료 배치 실패: {current_placement_error}') from current_placement_error
                current_result_rows=[[current_item['id'],current_item['frame']] for current_item in current_placements]
                return current_result_rows,current_result_rows,f'{len(current_result_rows)}개 키프레임 배치됨 · 공식 후처리 켜짐',True
            current_keyframe_add_endpoints.click(append_keyframe_endpoints,[current_keyframe_rows,current_keyframe_selector,current_frame_control],[current_keyframe_rows,current_keyframe_display,current_keyframe_notice,current_postprocessing_control])
            def remove_keyframe_placement(current_rows,current_target_number):
                if type(current_target_number) not in (int,float) or not float(current_target_number).is_integer():
                    raise gr.Error('삭제할 출력 프레임 번호를 입력하세요.')
                current_remaining_rows = [current_row for current_row in current_rows if current_row[1] != int(current_target_number)]
                if len(current_remaining_rows) == len(current_rows):
                    raise gr.Error('입력한 프레임에 배치된 키프레임이 없습니다.')
                return current_remaining_rows,current_remaining_rows,f'{len(current_remaining_rows)}개 키프레임 배치됨'
            current_keyframe_remove.click(remove_keyframe_placement,[current_keyframe_rows,current_keyframe_target],[current_keyframe_rows,current_keyframe_display,current_keyframe_notice])
            current_keyframe_clear.click(lambda:([],[],'배치 없음'),None,[current_keyframe_rows,current_keyframe_display,current_keyframe_notice])
            current_keyframe_rows.change(lambda current_rows:current_rows,current_keyframe_rows,current_keyframe_display,queue=False)
        gr.Markdown('### 출력 설정')
        current_horizontal_control = gr.Checkbox(label='제자리 보행 보정 · 수평 이동 제거',value=KIMODO_DEFAULT_SETTINGS['remove_horizontal_motion'],info='골반의 X·Z 이동을 제거하고 상하 움직임·관절 회전을 유지합니다. 걷기 자체를 만들지는 않으며 발 미끄러짐을 검수하세요. 원본 모션은 ZIP에 보존합니다.')
        current_scale_control=gr.Slider(minimum=10,maximum=100,step=0.5,value=KIMODO_DEFAULT_SETTINGS['openpose_scale_percent'],label='OpenPose 출력 크기 (%)',info='기본 85%. DWPose 검출 좌표를 영상 중심 기준 0.85배로 축소합니다. SOMA 렌더의 여백과 별개이며 프레임마다 같은 배율을 사용합니다. SOMA 원본은 변경하지 않습니다.')
        with gr.Accordion('OpenPose 신체 비율 참조 · 선택',open=False):
            current_proportions_control=gr.Checkbox(value=False,label='참조 이미지의 신체 비율을 OpenPose 출력에 적용')
            current_reference_control=gr.File(file_count='multiple',file_types=['.png'],label='같은 캐릭터 PNG 참조 · 최대 8장 · 장당 8MiB')
            current_reference_control.upload(lambda current_reference_paths: bool(current_reference_paths),current_reference_control,current_proportions_control,queue=False)
            current_proportion_status=gr.Markdown('신체 비율 보정: 미적용 · 참조 이미지를 첨부하면 적용을 켭니다.')
            def describe_proportion_selection(current_enabled_value,current_reference_paths):
                if current_reference_paths and not current_enabled_value:
                    return '⚠ 참조가 있지만 적용이 꺼져 있습니다. 적용을 켜거나 참조를 제거해야 생성할 수 있습니다.'
                if current_enabled_value and current_reference_paths:
                    return f'신체 비율 보정: 적용 · 참조 {len(current_reference_paths)}장 · DWPose 출력 관절 길이에 반영'
                return '신체 비율 보정: 참조 이미지가 필요합니다.' if current_enabled_value else '신체 비율 보정: 미적용'
            for current_selection_control in (current_reference_control,current_proportions_control):
                current_selection_control.change(describe_proportion_selection,[current_proportions_control,current_reference_control],current_proportion_status,queue=False)
            current_proportion_examples=load_proportion_examples()
            with gr.Row():
                current_proportion_selector=gr.Dropdown(choices=[(current_example_record['label'],current_example_identifier) for current_example_identifier,current_example_record in current_proportion_examples.items()],label='신체 비율 참조 예제',value=None,info='불러오면 참조 목록을 교체하고 비율 적용을 켭니다. 생성은 실행하지 않습니다.')
                current_proportion_button=gr.Button('참조 예제 불러오기')
            current_proportion_button.click(apply_proportion_example,current_proportion_selector,[current_proportions_control,current_reference_control],queue=False)
            build_input_preview(current_reference_control,'신체 비율 참조 미리보기 · 입력 순서')
            gr.Markdown('얼굴과 전신 관절이 보이는 참조를 권장합니다. 시트의 모든 인물을 검출하며 포즈 출력에만 비율을 적용합니다. 적용을 끄려면 참조도 제거하세요.')
            with gr.Accordion('참조 비율 추출과 한계',open=False):
                gr.Markdown('투명 PNG는 흰 배경으로 합성합니다. 관절 점수는 확률이 아닌 검출 점수이며 원시값을 보존합니다. 몸통 대비 너비·팔다리 비율과 코·어깨·골반의 거리 관계로 어깨선을 보정합니다. 코는 목뼈 위치가 아닌 대리 지표이며 측면·고개 방향·가림·원근에 따라 차이가 생길 수 있습니다. 유효한 부위·얼굴 관측이 없으면 중단하고 안내합니다. SOMA 원본·동작 방향은 유지합니다.')
        with gr.Row():
            current_hands_control = gr.Checkbox(value=False,label='DWPose 손 상세 포함',info='현재 시험에서는 주먹을 쥔 손가락 자세가 표현되지 않았습니다. 손 상세 포함은 DWPose 검출 결과를 표시하는 옵션이며 주먹 자세를 보장하지 않습니다.')
            current_face_control = gr.Checkbox(value=False,label='DWPose 얼굴 상세 포함')
        gr.Markdown('SOMA 렌더 → VideoX-Fun DWPose → 선택 참조 관절 길이 보정 → 832×480 · 30fps 포즈 MP4. Fun Control의 현행 입력은 16fps이므로 별도 변환이 필요합니다. 몸 18점의 코·눈·귀는 유지합니다.')
        current_prompt_control.change(describe_kimodo_prompt,[current_prompt_control,current_segment_control],current_prompt_summary,queue=False)
        current_segment_control.change(describe_kimodo_prompt,[current_prompt_control,current_segment_control],current_prompt_summary,queue=False)
        current_input_controls = [current_prompt_control,current_frame_control,current_steps_control,current_seed_control,current_guidance_control,current_heading_control,current_postprocessing_control,current_direction_control,current_horizontal_control,current_proportions_control,current_reference_control,current_scale_control,current_hands_control,current_face_control,current_segment_control,current_endpoint_selector,current_keyframe_rows,current_elevation_control]
        current_example_button.click(apply_complete_kimodo_example,current_example_selector,current_input_controls,queue=False)
        current_input_summary = gr.Markdown(describe_kimodo_input_summary(False,[],[],KIMODO_DEFAULT_SETTINGS['post_processing'],KIMODO_DEFAULT_SETTINGS['remove_horizontal_motion']))
        current_summary_inputs = [current_proportions_control,current_reference_control,current_keyframe_rows,current_postprocessing_control,current_horizontal_control]
        for current_summary_control in current_summary_inputs:
            current_summary_control.change(describe_kimodo_input_summary,current_summary_inputs,current_input_summary,queue=False)
        gr.Markdown('예시는 시작점입니다. 생성된 동작의 자세와 움직임을 검수하세요.')
        current_generate_button = gr.Button('대기열에 추가',variant='primary',interactive=False)
        build_button_guidance(current_generate_button,'모델 자료와 전용 환경을 준비한 뒤 상태를 새로 확인하고 동작 프롬프트와 출력 방향을 한 개 이상 선택하세요. 신체 비율 참조 옵션을 켰다면 RGB PNG 이미지를 첨부하세요. 키프레임을 배치했다면 공식 후처리를 켜고 수평 이동 제거를 해제하세요.')
        with gr.Column() as current_confirmation_container:
            pass
        gr.Markdown('### 진행 상태 · 최신 결과\n접수한 작업의 진행률·예상 시간·VRAM과 완료 영상을 표시합니다. 이전 작업은 아래 생성 이력에서 조회하세요.')
        current_job_control = build_generation_identifier('접수한 생성 ID')
        current_status_output = gr.Markdown('입력을 준비하세요.')
        def enqueue_kimodo_generation(*current_input_values):
            current_job_record = current_execute_command('generate',build_kimodo_payload(*current_input_values))
            return current_job_record['id'],'공용 GPU 대기열에 등록했습니다.'
        bind_gpu_generation_confirmation(current_generate_button,enqueue_kimodo_generation,current_input_controls,[current_job_control,current_status_output],generation_confirmation_container=current_confirmation_container,generation_readiness_callback=check_kimodo_readiness,generation_readiness_inputs=[current_model_ready,current_prompt_control,current_direction_control,current_proportions_control,current_reference_control,current_keyframe_rows,current_postprocessing_control,current_segment_control,current_endpoint_selector,current_horizontal_control],generation_readiness_events=[current_refresh_event,current_load_event])
        build_video_job_monitor(current_execute_command,current_server_address,current_job_control,current_status_output,result_renderer_callback=render_kimodo_result)
        current_read_history,current_history_outputs = build_generation_history_view(current_execute_command,current_server_address,GENERATION_CLEANUP_SCOPE_TEXT,restore_input_callback=restore_kimodo_inputs,restore_output_components=[*current_input_controls,current_job_control],result_renderer_callback=render_kimodo_result,record_folder_route='/kimodo',allow_individual_delete=True,individual_delete_scope_text=GENERATION_CLEANUP_SCOPE_TEXT)
        current_interface_blocks.load(lambda:current_read_history(1),outputs=current_history_outputs)
        with gr.Accordion('선택한 이력에서 키프레임 저장',open=False,elem_id='kimodo-history-keyframe-save'):
            gr.Markdown('위 생성 이력에서 완료된 작업을 선택하고 프레임을 불러오세요. 원본 SOMA 관절 미리보기는 30fps이며 첫 프레임은 1번입니다. 확인할 프레임으로 이동한 뒤 표시한 프레임 선택을 누르세요.')
            current_keyframe_number = gr.Number(label='원본 프레임 번호 · 1부터 시작',value=1,minimum=1,precision=0)
            current_keyframe_source = gr.State(None)
            current_keyframe_load_button = gr.Button('선택 이력 프레임 불러오기')
            from tools.review.common.gradio_frame_player import build_browser_frame_player
            current_keyframe_player = build_browser_frame_player('kimodo-keyframe-player',current_player_visible=True,defer_image_loading=False,current_selected_number_output=current_keyframe_number)
            current_keyframe_tag = gr.Textbox(label='키프레임 태그',max_lines=1,placeholder='예: 복싱 가드')
            current_keyframe_save = gr.Button('키프레임 저장',interactive=False)
            current_keyframe_status = gr.Markdown('이력 선택, 프레임 번호, 태그가 필요합니다.')
            current_keyframe_list_button = gr.Button('키프레임 목록 새로고침')
            current_keyframe_list_output = gr.JSON(label='저장된 키프레임 목록')
            def load_selected_keyframe_frames(current_job_identifier):
                if not current_job_identifier:
                    raise gr.Error('완료된 이력을 먼저 선택하세요.')
                current_job_status = current_execute_command('status',{'id':current_job_identifier})
                if current_job_status.get('status') != 'completed' or not current_job_status.get('attempt') or not current_job_status.get('image') or type(current_job_status.get('source_frame_count')) is not int:
                    raise gr.Error('완료된 모션 이력을 선택하세요.')
                current_frame_base = current_job_status['image'].rsplit('/',1)[0]
                current_frame_paths = [f'{current_frame_base}/output-{current_index:03d}.png' for current_index in range(current_job_status['source_frame_count'])]
                current_player_payload = {'frames':{'source':current_frame_paths},'directUrls':True,'panels':['원본 SOMA 관절 미리보기']}
                return json.dumps(current_player_payload,ensure_ascii=False),{'job_id':current_job_identifier,'attempt_id':current_job_status['attempt'],'frames':current_job_status['source_frame_count']},1,f"원본 {current_job_identifier} · {current_job_status['attempt']} · {len(current_frame_paths)}프레임을 불러왔습니다."
            current_keyframe_load_button.click(load_selected_keyframe_frames,current_history_outputs[0],[current_keyframe_player,current_keyframe_source,current_keyframe_number,current_keyframe_status])
            def update_keyframe_readiness(current_job_identifier,current_frame_value,current_tag_value,current_source_record):
                return gr.update(interactive=bool(current_source_record and current_source_record.get('job_id')==current_job_identifier and current_tag_value and current_tag_value.strip() and type(current_frame_value) in (int,float) and 1 <= current_frame_value <= current_source_record['frames'] and float(current_frame_value).is_integer()))
            for current_input_control in (current_history_outputs[0],current_keyframe_number,current_keyframe_tag,current_keyframe_source):
                current_input_control.change(update_keyframe_readiness,[current_history_outputs[0],current_keyframe_number,current_keyframe_tag,current_keyframe_source],current_keyframe_save,queue=False)
            def save_selected_keyframe(current_job_identifier,current_frame_value,current_tag_value,current_source_record):
                if not current_source_record or current_source_record.get('job_id') != current_job_identifier:
                    raise gr.Error('선택한 이력의 프레임을 다시 불러오세요.')
                current_job_status = current_execute_command('status',{'id':current_job_identifier})
                if current_job_status.get('status') != 'completed' or current_job_status.get('attempt') != current_source_record['attempt_id']:
                    raise gr.Error('작업 상태 또는 시도가 변경됐습니다. 프레임을 다시 불러오세요.')
                if type(current_frame_value) not in (int,float) or not float(current_frame_value).is_integer():
                    raise gr.Error('원본 프레임 번호는 정수여야 합니다.')
                current_saved_record = current_execute_command('keyframe-save',{'job_id':current_job_identifier,'attempt_id':current_source_record['attempt_id'],'frame':int(current_frame_value),'tag':current_tag_value})
                return f"저장 완료: {current_saved_record['id']} · {current_saved_record['tag']} · 원본 {current_saved_record['source_frame']}프레임"
            current_keyframe_save.click(save_selected_keyframe,[current_history_outputs[0],current_keyframe_number,current_keyframe_tag,current_keyframe_source],current_keyframe_status)
            current_keyframe_list_button.click(lambda:current_execute_command('keyframe-list',{})['records'],None,current_keyframe_list_output,queue=False)
    return current_interface_blocks
