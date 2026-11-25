"""Fun Control을 공용 대기열·이력에 연결한다."""
from workflow.common.reference_video_generation import ReferenceVideoGenerationManager
from workflow.domains.image.image_generation import ImageGenerationManager
from generators.wan_fun.contracts import reject_retired_rgb_input, FUN_JOB_STORAGE, FUN_PYTHON_EXECUTABLE, validate_fun_request, validate_fun_assets, inspect_fun_assets

class FunControlGenerationManager(ReferenceVideoGenerationManager):
    observe_legacy_prepare_history = True

    def __init__(self):
        super().__init__('/wan22-fun-control', FUN_JOB_STORAGE, 'generators/wan_fun/worker.py', validate_fun_request, validate_fun_assets, inspect_fun_assets)
        import threading
        self.current_request_lock = threading.RLock()

    def hold_generation_submission_guard(self):
        """동일 저장소를 사용하는 관리 프로세스의 접수를 직렬화한다."""
        from contextlib import contextmanager
        import fcntl
        import os
        import stat
        from pathlib import Path
        @contextmanager
        def acquire_fun_submission_guard():
            current_storage_root = Path(self.job_storage_root)
            if current_storage_root.is_symlink():
                raise ValueError('Wan Fun 작업 저장소 경로 오류')
            current_storage_root.mkdir(parents=True,exist_ok=True)
            try:
                current_lock_descriptor = os.open(current_storage_root/'.submission.lock',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW|os.O_NONBLOCK,0o666)
            except OSError as current_lock_error:
                raise ValueError('Wan Fun 접수 잠금을 확인할 수 없습니다.') from current_lock_error
            with os.fdopen(current_lock_descriptor,'a') as current_lock_handle:
                if not stat.S_ISREG(os.fstat(current_lock_handle.fileno()).st_mode):
                    raise ValueError('Wan Fun 접수 잠금은 일반 파일이어야 합니다.')
                try:
                    fcntl.flock(current_lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError as current_lock_error:
                    raise ValueError('Wan Fun의 다른 접수가 진행 중입니다. 다시 확인하세요.') from current_lock_error
                yield
        return acquire_fun_submission_guard()

    def resume_reviewed_generation_job(self, selected_job_directory, expected_fingerprint_value):
        """같은 관리기의 준비 접수와 배타적으로 검토한 생성 작업을 재개한다."""
        import json
        import re
        from pathlib import Path
        from workflow.common.gpu_job_queue import resume_gpu_generation
        from workflow.domains.image.image_generation import WORKFLOW_ROOT_PATH
        selected_job_directory = Path(selected_job_directory)
        if (not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',selected_job_directory.name)
                or selected_job_directory.is_symlink() or not selected_job_directory.is_dir()
                or selected_job_directory.parent.resolve() != Path(self.job_storage_root).resolve()):
            raise ValueError('Wan Fun 재개 작업 경로 오류')
        if not isinstance(expected_fingerprint_value,str) or not re.fullmatch(r'[a-f0-9]{64}',expected_fingerprint_value):
            raise ValueError('Wan Fun 재개 확인값 오류')
        with self.hold_generation_submission_guard(), self.current_request_lock:
            if self.inspect_video_resume_availability() != 'available':
                raise ValueError('Wan Fun 모델 준비 중이거나 준비 상태를 확인할 수 없습니다.')
            if self.fingerprint_generation_resume_inputs(selected_job_directory)['fingerprint'] != expected_fingerprint_value:
                raise ValueError('검토한 Wan Fun 재개 입력이 변경됐습니다.')
            current_request_record = json.loads((selected_job_directory/'request.json').read_text())
            current_command_values = [str(self.select_generation_python(current_request_record)),str(WORKFLOW_ROOT_PATH/self.select_generation_runner(current_request_record)),'--job-dir',str(selected_job_directory)]
            current_service_value = self.select_generation_service(current_request_record)
            def validate_locked_fun_resume(current_job_directory):
                if self.inspect_video_resume_availability() != 'available':
                    raise ValueError('Wan Fun 모델 준비 중이거나 준비 상태를 확인할 수 없습니다.')
                if self.fingerprint_generation_resume_inputs(current_job_directory)['fingerprint'] != expected_fingerprint_value:
                    raise ValueError('검토한 Wan Fun 재개 입력이 변경됐습니다.')
                current_locked_request = json.loads((current_job_directory/'request.json').read_text())
                current_locked_command = [str(self.select_generation_python(current_locked_request)),str(WORKFLOW_ROOT_PATH/self.select_generation_runner(current_locked_request)),'--job-dir',str(current_job_directory)]
                if current_locked_command != current_command_values or self.select_generation_service(current_locked_request) != current_service_value:
                    raise ValueError('검토한 Wan Fun 실행 명령이 변경됐습니다.')
                self.validate_generation_resume(current_job_directory, recover_interrupted_value=False)
                if self.fingerprint_generation_resume_inputs(current_job_directory)['fingerprint'] != expected_fingerprint_value:
                    raise ValueError('Wan Fun 재개 검증 중 입력이 변경됐습니다.')
            return resume_gpu_generation(selected_job_directory, legacy_command_record={'command':current_command_values,'service':current_service_value}, expected_resume_service=current_service_value, expected_resume_command=current_command_values, resume_locked_preflight_callback=validate_locked_fun_resume)

    def validate_generation_resume_target(self, selected_job_directory):
        from pathlib import Path
        selected_job_directory = Path(selected_job_directory)
        if (selected_job_directory.is_symlink() or not selected_job_directory.is_dir()
                or selected_job_directory.parent.resolve() != Path(self.job_storage_root).resolve()):
            raise ValueError('Wan Fun 재개 작업 경로 오류')

    def resume_generation_job(self, selected_job_directory, saved_request_record, legacy_command_record):
        """기존 직접 재개도 공용 접수 잠금 아래 입력과 준비 상태를 확인한다."""
        import json
        from pathlib import Path
        from workflow.common.gpu_job_queue import resume_gpu_generation
        from workflow.domains.image.image_generation import WORKFLOW_ROOT_PATH
        selected_job_directory = Path(selected_job_directory)
        self.validate_generation_resume_target(selected_job_directory)
        with self.hold_generation_submission_guard(), self.current_request_lock:
            if self.inspect_video_resume_availability() != 'available':
                raise ValueError('Wan Fun 모델 준비 중이거나 준비 상태를 확인할 수 없습니다.')
            current_request_record = json.loads((selected_job_directory/'request.json').read_text())
            if current_request_record != saved_request_record:
                raise ValueError('Wan Fun 재개 요청 기록이 변경됐습니다.')
            current_command_values = [str(self.select_generation_python(current_request_record)),str(WORKFLOW_ROOT_PATH/self.select_generation_runner(current_request_record)),'--job-dir',str(selected_job_directory)]
            current_service_value = self.select_generation_service(current_request_record)
            def validate_locked_fun_resume(current_job_directory):
                if self.inspect_video_resume_availability() != 'available':
                    raise ValueError('Wan Fun 모델 준비 중이거나 준비 상태를 확인할 수 없습니다.')
                current_locked_request = json.loads((current_job_directory/'request.json').read_text())
                if current_locked_request != current_request_record:
                    raise ValueError('Wan Fun 재개 요청 기록이 변경됐습니다.')
                self.validate_generation_resume(current_job_directory, recover_interrupted_value=False)
            return resume_gpu_generation(selected_job_directory, legacy_command_record=legacy_command_record, expected_resume_service=current_service_value, expected_resume_command=current_command_values, resume_locked_preflight_callback=validate_locked_fun_resume)

    def select_generation_python(self, saved_request_record=None):
        if saved_request_record and saved_request_record.get('action') == 'prepare':
            return FUN_JOB_STORAGE.parents[2] / '.venv/bin/python'
        return FUN_PYTHON_EXECUTABLE

    def select_generation_runner(self, saved_request_record=None):
        if saved_request_record and saved_request_record.get('action') == 'prepare':
            return 'generators/wan_fun/prepare_worker.py'
        return super().select_generation_runner(saved_request_record)

    def select_generation_service(self, saved_request_record=None):
        if saved_request_record and saved_request_record.get('action') == 'prepare':
            return 'wan-fun-prepare'
        return 'wan-fun'

    def validate_generation_request(self, current_request_record):
        if isinstance(current_request_record, dict) and current_request_record.get('model_profile') == 'wan21-1.3b':
            raise ValueError('Wan 2.1 Fun Control 실험은 폐기되었습니다.')
        if current_request_record == {'action': 'prepare'}:
            return {'action': 'prepare', 'images': []}
        return super().validate_generation_request(current_request_record)

    def ensure_generation_request_available(self, current_request_record):
        if current_request_record.get('action') != 'prepare' or not self.job_storage_root.exists():
            return
        import json
        for current_job_directory in self.job_storage_root.iterdir():
            current_request_path = current_job_directory / 'request.json'
            current_status_path = current_job_directory / 'status.json'
            if not current_request_path.is_file() or not current_status_path.is_file():
                continue
            current_saved_request = json.loads(current_request_path.read_text())
            if current_saved_request.get('action') == 'prepare':
                from workflow.common.video_job_recovery import recover_interrupted_video_job
                recover_interrupted_video_job(current_job_directory)
            current_saved_status = json.loads(current_status_path.read_text())
            if current_saved_request.get('action') == 'prepare' and current_saved_status.get('status') in ('queued', 'running'):
                raise ValueError(f'모델 준비가 이미 진행 중입니다: {current_job_directory.name}')
        if self.inspect_video_resume_availability() != 'available':
            raise ValueError('Wan Fun 준비 작업 상태를 확인할 수 없어 새 준비를 보류합니다.')

    def validate_video_preview_job_type(self, selected_job_directory):
        """모델 준비 작업은 상태 복구를 수행하기 전 검토에서 제외한다."""
        import json
        import os
        import stat
        try:
            current_record_descriptor = os.open(selected_job_directory/'request.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(current_record_descriptor,'rb') as current_record_stream:
                current_record_stat = os.fstat(current_record_stream.fileno())
                if not stat.S_ISREG(current_record_stat.st_mode) or current_record_stat.st_size > 8 * 1024 * 1024:
                    raise ValueError('Wan Fun 요청 기록 오류')
                current_request_bytes = current_record_stream.read(8 * 1024 * 1024 + 1)
                if len(current_request_bytes) > 8 * 1024 * 1024:
                    raise ValueError('Wan Fun 요청 기록 크기 오류')
                current_request_record = json.loads(current_request_bytes)
            if not isinstance(current_request_record,dict) or current_request_record.get('action') != 'generate':
                raise ValueError('Wan Fun 생성 작업만 재개 검토할 수 있습니다.')
        except (OSError, UnicodeError, json.JSONDecodeError) as current_record_error:
            raise ValueError('Wan Fun 요청 기록을 확인할 수 없습니다.') from current_record_error

    def inspect_video_resume_availability(self):
        """저장된 준비 작업을 확인하며 확인 불가는 유휴로 취급하지 않는다."""
        import json
        import os
        import re
        import stat
        from pathlib import Path
        def read_bounded_preparation_record(current_record_path):
            current_record_descriptor = os.open(current_record_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(current_record_descriptor, 'rb') as current_record_stream:
                current_record_stat = os.fstat(current_record_stream.fileno())
                if not stat.S_ISREG(current_record_stat.st_mode) or current_record_stat.st_size > 1048576:
                    raise ValueError('준비 작업 기록 오류')
                current_record_bytes = current_record_stream.read(1048577)
                if len(current_record_bytes) > 1048576:
                    raise ValueError('준비 작업 기록 크기 오류')
                current_record_value = json.loads(current_record_bytes)
                if not isinstance(current_record_value, dict):
                    raise ValueError('준비 작업 기록 형식 오류')
                return current_record_value
        try:
            with self.current_request_lock:
                current_storage_root = Path(self.job_storage_root)
                if current_storage_root.is_symlink() or not current_storage_root.is_dir():
                    return 'unknown'
                for current_job_path in current_storage_root.iterdir():
                    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-(?:[a-f0-9]{8}|prepare)',current_job_path.name):
                        continue
                    if current_job_path.is_symlink() or not current_job_path.is_dir():
                        raise ValueError('준비 작업 디렉터리 오류')
                    current_request_record = read_bounded_preparation_record(current_job_path/'request.json')
                    if current_request_record.get('action') is None:
                        # 구형 생성 기록은 action이 없을 수 있다. 종료 상태와 실제 생성 작업자 명령이
                        # 모두 확인된 경우에만 준비 작업이 아닌 것으로 분류한다.
                        from workflow.domains.image.image_generation import WORKFLOW_ROOT_PATH
                        current_legacy_status = read_bounded_preparation_record(current_job_path/'status.json')
                        current_legacy_command = read_bounded_preparation_record(current_job_path/'gpu-command.json')
                        current_expected_command = [str(self.select_generation_python(current_request_record)), str(WORKFLOW_ROOT_PATH/self.select_generation_runner(current_request_record)), '--job-dir', str(current_job_path)]
                        if (current_legacy_status.get('status') not in ('completed', 'failed', 'cancelled', 'canceled')
                                or current_legacy_command != {'command': current_expected_command, 'service': 'wan-fun'}
                                or not isinstance(current_request_record.get('references'), list)
                                or not isinstance(current_request_record.get('frames'), int)):
                            raise ValueError('구형 생성 기록의 종류를 확인할 수 없습니다.')
                        continue
                    if current_request_record.get('action') not in ('generate','prepare'):
                        raise ValueError('작업 종류 확인 불가')
                    if current_request_record['action'] != 'prepare':
                        continue
                    current_status_record = read_bounded_preparation_record(current_job_path/'status.json')
                    current_status_value = current_status_record.get('status')
                    if current_status_value in ('queued','running'):
                        return 'download_running'
                    if current_status_value not in ('completed','failed','cancelled','canceled'):
                        raise ValueError('준비 작업 상태 확인 불가')
            return 'available'
        except (OSError, ValueError, TypeError, UnicodeError):
            return 'unknown'

    def validate_generation_runtime(self, saved_request_record=None):
        if saved_request_record and saved_request_record.get('action') == 'prepare':
            return
        if saved_request_record and saved_request_record.get('model_profile') == 'wan21-1.3b':
            raise ValueError('Wan 2.1 Fun Control 실험은 폐기되어 재개할 수 없습니다.')
        else:
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

    def validate_generation_resume(self, selected_job_directory, recover_interrupted_value=True):
        import json
        current_request_record = json.loads((selected_job_directory/'request.json').read_text())
        reject_retired_rgb_input(current_request_record)
        if current_request_record.get('action') == 'prepare':
            self.validate_generation_runtime(current_request_record)
            return
        if current_request_record.get('action') != 'generate':
            raise ValueError('Fun Control 재개 작업 종류 오류')
        from workflow.domains.image.three_reference_generation import verify_reference_snapshots
        from workflow.common.video_attachment_verification import verify_saved_video_attachments
        current_video_fields = tuple(current_field_name for current_field_name in ('pose_video','driving_video') if current_field_name+'_file' in current_request_record or current_field_name+'_sha256' in current_request_record)
        if len(current_video_fields) > 1:
            raise ValueError('포즈 영상과 동작 영상은 함께 사용할 수 없습니다.')
        current_frame_count = current_request_record.get('frames')
        current_reference_names = current_request_record.get('references')
        if type(current_frame_count) is not int or current_frame_count < 1 or not isinstance(current_reference_names,list) or len(current_reference_names) != (1 if current_video_fields else current_frame_count + 1):
            raise ValueError('Fun Control 재개 참조 이미지 개수 오류')
        verify_reference_snapshots(selected_job_directory, current_request_record)
        verify_saved_video_attachments(selected_job_directory, current_request_record, current_video_fields, attachment_filename_overrides={'pose_video':'pose-input.mp4'}, allow_legacy_missing_hash=True)
        self.validate_generation_runtime(current_request_record)

    def read_generation_status_record(self, current_job_root, fallback_status_record=None, include_log_value=False):
        import json
        current_request_path = current_job_root / 'request.json'
        if current_request_path.is_file() and json.loads(current_request_path.read_text()).get('action') == 'prepare':
            from workflow.common.video_job_recovery import recover_interrupted_video_job, normalize_recovered_video_metrics
            recover_interrupted_video_job(current_job_root)
            current_status_record = ImageGenerationManager.read_generation_status_record(self, current_job_root, fallback_status_record, include_log_value)
            normalize_recovered_video_metrics(current_status_record)
            return current_status_record
        current_status_record = super().read_generation_status_record(current_job_root, fallback_status_record, include_log_value)
        if current_status_record.get('video'):
            import json
            current_result_record = json.loads((current_job_root/'result.json').read_text())
            if (current_job_root/'attempts'/current_result_record['attempt']/'pose.mp4').is_file():
                current_status_record['preprocess_videos'] = {'VideoX-Fun 포즈 추출': current_status_record['video'].rsplit('/', 1)[0]+'/pose.mp4'}
        return current_status_record
