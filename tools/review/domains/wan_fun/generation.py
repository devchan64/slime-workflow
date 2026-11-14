"""Fun Control을 공용 대기열·이력에 연결한다."""
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager
from tools.review.domains.image.image_generation import ImageGenerationManager
from generators.wan_fun.contracts import reject_retired_rgb_input, FUN_JOB_STORAGE, FUN_PYTHON_EXECUTABLE, validate_fun_request, validate_fun_assets, inspect_fun_assets

class FunControlGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan22-fun-control', FUN_JOB_STORAGE, 'generators/wan_fun/worker.py', validate_fun_request, validate_fun_assets, inspect_fun_assets)

    def select_generation_python(self, saved_request_record=None):
        if saved_request_record and saved_request_record.get('action') == 'prepare':
            return FUN_JOB_STORAGE.parents[2] / '.venv/bin/python'
        return FUN_PYTHON_EXECUTABLE

    def select_generation_runner(self, saved_request_record=None):
        if saved_request_record and saved_request_record.get('action') == 'prepare':
            return 'generators/wan_fun/prepare_worker.py'
        return super().select_generation_runner(saved_request_record)

    def validate_generation_request(self, current_request_record):
        if current_request_record == {'action': 'prepare'}:
            return {'action': 'prepare', 'images': []}
        return super().validate_generation_request(current_request_record)

    def validate_generation_runtime(self, saved_request_record=None):
        if saved_request_record and saved_request_record.get('action') == 'prepare':
            return
        super().validate_generation_runtime(saved_request_record)
        if saved_request_record and ('driving_video' in saved_request_record or 'driving_video_file' in saved_request_record):
            from generators.wan_fun.pose_preprocess import validate_fun_pose_assets
            validate_fun_pose_assets()

    def save_generation_attachments(self, current_job_root, current_request_record):
        reject_retired_rgb_input(current_request_record)
        current_request_record = dict(current_request_record)
        if 'pose_video' in current_request_record:
            import base64,hashlib
            current_video_bytes = base64.b64decode(current_request_record['pose_video'],validate=True)
            (current_job_root/'pose-input.mp4').write_bytes(current_video_bytes)
            return {**{current_field_name:current_field_value for current_field_name,current_field_value in current_request_record.items() if current_field_name!='pose_video'},'pose_video_file':'pose-input.mp4','pose_video_sha256':hashlib.sha256(current_video_bytes).hexdigest(),'control_preprocessor':'none'}
        if 'driving_video' not in current_request_record:
            return current_request_record
        import base64
        import hashlib
        current_video_bytes = base64.b64decode(current_request_record['driving_video'], validate=True)
        (current_job_root/'driving.mp4').write_bytes(current_video_bytes)
        return {**{current_field_name: current_field_value for current_field_name, current_field_value in current_request_record.items() if current_field_name!='driving_video'}, 'driving_video_file': 'driving.mp4', 'driving_video_sha256': hashlib.sha256(current_video_bytes).hexdigest(), 'control_preprocessor': 'videox-fun-dwpose'}

    def validate_generation_resume(self, selected_job_directory):
        import json
        current_request_record = json.loads((selected_job_directory/'request.json').read_text())
        reject_retired_rgb_input(current_request_record)
        self.validate_generation_runtime(current_request_record)

    def read_generation_status_record(self, current_job_root, fallback_status_record=None, include_log_value=False):
        import json
        current_request_path = current_job_root / 'request.json'
        if current_request_path.is_file() and json.loads(current_request_path.read_text()).get('action') == 'prepare':
            return ImageGenerationManager.read_generation_status_record(self, current_job_root, fallback_status_record, include_log_value)
        current_status_record = super().read_generation_status_record(current_job_root, fallback_status_record, include_log_value)
        if current_status_record.get('video'):
            import json
            current_result_record = json.loads((current_job_root/'result.json').read_text())
            if (current_job_root/'attempts'/current_result_record['attempt']/'pose.mp4').is_file():
                current_status_record['preprocess_videos'] = {'VideoX-Fun 포즈 추출': current_status_record['video'].rsplit('/', 1)[0]+'/pose.mp4'}
        return current_status_record
