"""생성 서비스와 대화 화면이 공유하는 미디어 결과 경로 검증."""
import re


def validate_hermes_video_result_paths(current_service_name,current_job_identifier,current_job_record):
    """완료된 한 시도의 고정 결과 경로만 반환한다."""
    current_result_paths={'video':None,'image':None,'download':None}
    if not isinstance(current_job_record,dict) or current_job_record.get('status')!='completed' or current_job_record.get('result_error'):
        return current_result_paths
    current_attempt_values=set()
    for current_field_name,current_file_name in (('video','preview.mp4'),('image','output-000.png'),('download','frames.zip')):
        current_path_value=current_job_record.get(current_field_name)
        current_path_pattern='/'+re.escape(current_service_name)+'/jobs/'+re.escape(current_job_identifier)+r'/attempts/([a-f0-9]{32})/'+re.escape(current_file_name)
        current_path_match=re.fullmatch(current_path_pattern,current_path_value) if isinstance(current_path_value,str) else None
        if current_path_match:
            current_result_paths[current_field_name]=current_path_value
            current_attempt_values.add(current_path_match.group(1))
    return {current_field_name:None for current_field_name in current_result_paths} if len(current_attempt_values)>1 else current_result_paths


def validate_hermes_audio_result_path(current_service_name,current_job_identifier,current_job_record):
    """완료된 오디오 작업의 지정 음원 경로만 반환한다."""
    if not isinstance(current_job_record,dict) or current_job_record.get('status')!='completed':return None
    current_path_value=current_job_record.get('audio')
    current_file_name='music.wav' if current_service_name=='music-heartmula' else 'sound.wav'
    current_path_pattern='/'+re.escape(current_service_name)+'/jobs/'+re.escape(current_job_identifier)+r'/attempts/[a-f0-9]{32}/'+re.escape(current_file_name)
    return current_path_value if isinstance(current_path_value,str) and re.fullmatch(current_path_pattern,current_path_value) else None
