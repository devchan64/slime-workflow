"""Fun Control을 공용 대기열·이력에 연결한다."""
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager
from generators.wan_fun.contracts import FUN_JOB_STORAGE, validate_fun_request, validate_fun_assets, inspect_fun_assets

class FunControlGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan22-fun-control', FUN_JOB_STORAGE, 'generators/wan_fun/worker.py', validate_fun_request, validate_fun_assets, inspect_fun_assets)

    def validate_generation_runtime(self, saved_request_record=None):
        super().validate_generation_runtime(saved_request_record)
        if saved_request_record and ('driving_video' in saved_request_record or 'driving_video_file' in saved_request_record):
            from generators.wan_fun.pose_preprocess import validate_fun_pose_assets
            validate_fun_pose_assets()

    def save_generation_attachments(self, current_job_root, current_request_record):
        if 'driving_video' not in current_request_record:
            return current_request_record
        import base64
        import hashlib
        current_video_bytes = base64.b64decode(current_request_record['driving_video'], validate=True)
        (current_job_root/'driving.mp4').write_bytes(current_video_bytes)
        return {**{current_field_name: current_field_value for current_field_name, current_field_value in current_request_record.items() if current_field_name!='driving_video'}, 'driving_video_file': 'driving.mp4', 'driving_video_sha256': hashlib.sha256(current_video_bytes).hexdigest(), 'control_preprocessor': 'videox-fun-dwpose'}

    def validate_generation_resume(self, selected_job_directory):
        import json
        self.validate_generation_runtime(json.loads((selected_job_directory/'request.json').read_text()))

    def read_generation_status_record(self, current_job_root, fallback_status_record=None, include_log_value=False):
        current_status_record = super().read_generation_status_record(current_job_root, fallback_status_record, include_log_value)
        if current_status_record.get('video'):
            import json
            current_result_record = json.loads((current_job_root/'result.json').read_text())
            if (current_job_root/'attempts'/current_result_record['attempt']/'pose.mp4').is_file():
                current_status_record['preprocess_videos'] = {'VideoX-Fun 포즈 추출': current_status_record['video'].rsplit('/', 1)[0]+'/pose.mp4'}
        return current_status_record
