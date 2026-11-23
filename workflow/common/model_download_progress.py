"""모델 서비스별 다운로드 이력과 전송량 표시."""
MODEL_DOWNLOAD_PREFIXES = {
    'wan22-i2v-assets': ('wan22-i2v-assets/',),
    'wan22-fighting-lora': ('wan22-fighting-lora/',),
    'wan22-vace-q8': ('wan22-vace-q8/',),
    'wan22-vace-lightning': ('wan22-vace-lightning/',),
    'animationgpt': ('animationgpt/',),
    'flux-image': ('black-forest-labs/flux-3-image-klein',),
    'prop-generator': ('Qwen/Qwen-Image-2.1',),
    'expression-lora': ('WarmBloodAban/Qwen-Image-2.1-LoRAs',),
    'dwpose': ('yzd-v/DWPose',),
    'kimodo': ('nvidia/Kimodo', 'McGill-NLP/LLM2Vec', 'ollama/llama3', 'Wan-AI/Wan2.2-Animate-14B'),
    'wan22-animate2': ('Wan-AI/Wan2.2-Animate-2-14B-Diffusers',),
    'wan22-fun-control': ('Comfy-Org/Wan-2.2', 'Comfy-Org/Wan-2.1/split_files/text_encoders/', 'Comfy-Org/Wan-2.1/split_files/vae/', 'yzd-v/DWPose'),
    'wan21-fun-1.3b': ('alibaba-pai/Wan2.1-Fun-V1.1-1.3B-Control', 'Comfy-Org/Wan-2.1/split_files/clip_vision/clip_vision_h.safetensors'),
    'wan22-vace': ('wan22-vace/', 'wan-vace/', 'QuantStack/Wan2.2-VACE', 'alibaba-pai/Wan2.2-VACE', 'Comfy-Org/Wan-2.1/split_files/vae/wan_2.1_vae.safetensors'),
    'music-heartmula': ('HeartMuLa/', 'heartmula/'),
    'sfx-dasheng-audiogen': ('mispeech/Dasheng-AudioGen', 'mispeech/dashengtokenizer', 'google/flan-t5-large'),
    'writer-agent': ('writer-agent/',),
    'hermes-model': ('hermes-agent/',),
    'prompt-translation': ('google/translategemma-4b-it',),
}


def matches_model_download(model_service_name, model_name):
    return isinstance(model_name, str) and (model_service_name == 'wan22-vace' and model_name == 'wan22-vace' or model_name.startswith(MODEL_DOWNLOAD_PREFIXES[model_service_name]))


def format_model_download_status(current_status_values, model_service_name):
    current_matching_values = [current_status_value for current_status_value in current_status_values
                               if matches_model_download(model_service_name, current_status_value.get('model'))]
    current_active_values = [current_status_value for current_status_value in current_matching_values if current_status_value.get('status') == 'running']
    current_recent_values = [current_status_value for current_status_value in current_matching_values if current_status_value.get('status') in ('completed', 'failed', 'interrupted')]
    current_status_labels = {'running': '진행 중', 'completed': '완료', 'failed': '실패', 'interrupted': '중단됨'}
    current_result_lines = []
    for current_status_value in current_active_values + current_recent_values[:1]:
        current_received_bytes = current_status_value.get('bytes', 0)
        current_total_bytes = current_status_value.get('total_bytes')
        current_progress_text = f'{current_received_bytes / current_total_bytes * 100:.1f}% ({current_received_bytes:,} / {current_total_bytes:,}바이트)' if current_total_bytes else f'{current_received_bytes:,}바이트 · 전체 크기 확인 중'
        current_status_name = current_status_value['status']
        if current_status_name == 'completed' and not current_total_bytes:
            current_progress_text = '모델 준비 상태 확인' if current_status_value.get('stage') == '준비 완료' else '크기 정보 없음'
        elif current_status_name == 'completed' and current_total_bytes and current_received_bytes != current_total_bytes:
            current_progress_text = '전송량 기록 불일치 · 파일 준비 상태 확인'
        current_existing_bytes = current_status_value.get('existing_bytes')
        if current_status_value.get('stage') == '기존 부분 파일 검증' and isinstance(current_existing_bytes, int) and current_existing_bytes > 0:
            current_progress_text = (f'기존 부분 {current_existing_bytes:,}바이트 보존 · '
                                     f'검증 {current_received_bytes / current_existing_bytes * 100:.1f}% '
                                     f'({current_received_bytes:,} / {current_existing_bytes:,}바이트)')
        elif current_status_value.get('stage') == '기존 부분 파일 검증':
            # 이전 버전에서 시작한 작업은 기존 부분 크기를 보고하지 않는다.
            current_progress_text = f'검증한 데이터 {current_received_bytes:,}바이트 · 전체 파일 기준 {current_progress_text}'
        current_resume_bytes = current_status_value.get('resumed_bytes')
        current_resume_text = f'{current_resume_bytes:,}바이트' if current_resume_bytes is not None else '확인 불가'
        current_resume_label = '시작 시 검증 지점' if current_status_value.get('stage') == '기존 부분 파일 검증' else '시작 시 이어받은 바이트'
        current_resume_suffix = f' · {current_resume_label} {current_resume_text}' if current_resume_bytes is not None or current_status_name == 'running' else ''
        current_result_lines.append(f"- {current_status_value['model']} · {current_status_labels[current_status_name]} · {current_status_value.get('stage', '준비')} · {current_progress_text}{current_resume_suffix}")
    return '\n'.join(current_result_lines) if current_result_lines else '진행 중인 다운로드와 최근 결과가 없습니다.'
