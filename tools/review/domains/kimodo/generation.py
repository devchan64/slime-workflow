"""공용 대기열·누적 이력·실제 파일 삭제 계약을 사용하는 Kimodo 서비스."""
from generators.kimodo.contracts import KIMODO_JOB_STORAGE,inspect_kimodo_assets,validate_kimodo_assets,validate_kimodo_request
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager

class KimodoGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/kimodo',KIMODO_JOB_STORAGE,'generators/kimodo/worker.py',validate_kimodo_request,validate_kimodo_assets,inspect_kimodo_assets)
        from tools.review.domains.kimodo.keyframe_storage import KIMODO_KEYFRAME_STORAGE
        self.keyframe_storage_root = KIMODO_KEYFRAME_STORAGE

    def handle_image_request(self, current_http_handler):
        """게이트웨이에서 검증한 키프레임 저장·목록 명령을 처리한다."""
        import json
        from urllib.parse import urlsplit
        current_request_path = urlsplit(current_http_handler.path).path
        if current_request_path not in ('/kimodo/keyframes/save', '/kimodo/keyframes/list', '/kimodo/keyframes/preview'):
            return super().handle_image_request(current_http_handler)
        try:
            if current_http_handler.command != 'POST' or not hasattr(current_http_handler, 'management_command_payload'):
                raise ValueError('키프레임 명령은 공용 게이트웨이를 통해 요청해야 합니다.')
            current_request_record = current_http_handler.management_command_payload
            if not isinstance(current_request_record, dict):
                raise ValueError('키프레임 요청은 객체여야 합니다.')
            from tools.review.domains.kimodo.keyframe_storage import list_kimodo_keyframe_records, save_kimodo_keyframe_record, load_kimodo_keyframe_snapshot
            from tools.review.domains.image.image_generation import MANAGER_HISTORY_LOCK
            if current_request_path.endswith('/list'):
                if current_request_record:
                    raise ValueError('키프레임 목록은 입력을 받지 않습니다.')
                current_response_record = {'records': list_kimodo_keyframe_records(self.keyframe_storage_root)}
            elif current_request_path.endswith('/preview'):
                if set(current_request_record) != {'id'}:
                    raise ValueError('키프레임 미리보기에는 ID가 필요합니다.')
                import base64
                current_keyframe_record,_,_ = load_kimodo_keyframe_snapshot(self.keyframe_storage_root,current_request_record['id'])
                current_preview_bytes=(self.keyframe_storage_root/current_keyframe_record['id']/'preview.png').read_bytes()
                current_response_record={'record':current_keyframe_record,'image_base64':base64.b64encode(current_preview_bytes).decode('ascii')}
            else:
                if set(current_request_record) != {'job_id', 'attempt_id', 'frame', 'tag'}:
                    raise ValueError('키프레임 저장 필드 오류')
                with self.current_request_lock, MANAGER_HISTORY_LOCK:
                    current_response_record = save_kimodo_keyframe_record(current_request_record['job_id'],current_request_record['attempt_id'],current_request_record['frame'],current_request_record['tag'],current_job_storage=self.job_storage_root,current_keyframe_storage=self.keyframe_storage_root)
            current_response_status = 200
        except (ValueError, OSError, KeyError, TypeError) as current_request_error:
            current_response_record = {'error': str(current_request_error)}
            current_response_status = 400
        current_response_bytes = json.dumps(current_response_record,ensure_ascii=False).encode()
        current_http_handler.send_response(current_response_status)
        current_http_handler.send_header('Content-Type','application/json; charset=utf-8')
        current_http_handler.send_header('Content-Length',str(len(current_response_bytes)))
        current_http_handler.end_headers()
        current_http_handler.wfile.write(current_response_bytes)
        return True

    def validate_generation_runtime(self,saved_request_record=None):
        super().validate_generation_runtime(saved_request_record)
        from generators.kimodo.dwpose_runtime import validate_fun_pose_assets
        validate_fun_pose_assets()
        if saved_request_record and (saved_request_record.get('images') or saved_request_record.get('references')):
            from generators.kimodo.reference_extraction import validate_reference_pose_runtime
            validate_reference_pose_runtime()

    def validate_generation_request(self, current_request_record):
        current_validated_request = super().validate_generation_request(current_request_record)
        if current_validated_request.get('keyframes'):
            from tools.review.domains.kimodo.keyframe_storage import load_kimodo_keyframe_snapshot
            for current_placement_record in current_validated_request['keyframes']:
                load_kimodo_keyframe_snapshot(self.keyframe_storage_root,current_placement_record['id'])
        return current_validated_request

    def validate_generation_resume(self,selected_job_directory):
        import json
        current_saved_request=json.loads((selected_job_directory/'request.json').read_text())
        if current_saved_request.get('action')=='reference-analysis':
            raise ValueError('참조 추출 검증은 모션 생성 재개 대상이 아닙니다. 참조 입력을 불러와 새 작업을 생성하세요.')
        if current_saved_request.get('keyframes'):
            from tools.review.domains.kimodo.keyframe_storage import validate_kimodo_job_keyframe_snapshots
            validate_kimodo_job_keyframe_snapshots(selected_job_directory,current_saved_request)
        self.validate_generation_runtime(current_saved_request)

    def save_generation_attachments(self, current_job_root, current_request_record):
        current_saved_record = super().save_generation_attachments(current_job_root, current_request_record)
        if current_saved_record.get('keyframes'):
            from tools.review.domains.kimodo.keyframe_storage import snapshot_kimodo_keyframes
            current_snapshot_records = snapshot_kimodo_keyframes(current_job_root,current_saved_record['keyframes'],current_keyframe_storage=self.keyframe_storage_root)
            current_saved_record = {**current_saved_record,'keyframe_snapshots':current_snapshot_records}
        return current_saved_record

    def read_generation_status_record(self,current_job_root,fallback_status_record=None,include_log_value=False):
        current_status_record = super().read_generation_status_record(current_job_root,fallback_status_record,include_log_value)
        if current_status_record.get('video'):
            import json
            current_result_record = json.loads((current_job_root/'result.json').read_text())
            current_frame_count=current_result_record.get('frames')
            if type(current_frame_count) is int and current_frame_count > 0:
                current_status_record['source_frame_count']=current_frame_count
            current_status_record['dwpose_status']=current_result_record.get('dwpose_status','completed' if current_result_record.get('dwpose_videos') else 'unrecorded')
            current_status_record['direct_pose_status']='completed' if current_result_record.get('direct_pose_videos') else 'unrecorded'
            current_status_record['quality_warnings']=current_result_record.get('quality_warnings',[])
            current_error_path=current_job_root/'attempts'/current_result_record['attempt']/'dwpose-error.json'
            if current_error_path.is_file():
                current_status_record['dwpose_error']=json.loads(current_error_path.read_text())['error']
            elif current_status_record['dwpose_status']=='warning':
                # 구조화 오류가 없던 과거 기록에서 명시된 검출 오류만 읽는다.
                import re
                current_log_path=current_job_root/'worker.log'
                if current_log_path.is_file():
                    with current_log_path.open('rb') as current_log_stream:
                        current_log_stream.seek(max(0,current_log_path.stat().st_size-32768))
                        current_log_tail=current_log_stream.read().decode(errors='replace')
                    current_error_matches=re.findall(r'^ValueError: (단일 인체 검출 필요: \d+프레임)$',current_log_tail,re.MULTILINE)
                    if current_error_matches:
                        current_status_record['dwpose_error']=current_error_matches[-1]
            if current_result_record.get('soma_render_videos'):
                current_status_record['preprocess_videos'] = {f'SOMA 렌더 · {current_direction_name}': current_status_record['video'].rsplit('/', 1)[0]+'/'+current_video_name for current_direction_name, current_video_name in current_result_record['soma_render_videos'].items()}
            if current_result_record.get('direct_pose_videos'):
                current_status_record.setdefault('preprocess_videos',{}).update({f'직접 포즈 · {current_direction_name}':current_status_record['video'].rsplit('/',1)[0]+'/'+current_video_name for current_direction_name,current_video_name in current_result_record['direct_pose_videos'].items()})
            if current_result_record.get('dwpose_videos'):
                current_status_record.setdefault('preprocess_videos',{}).update({f'DWPose 포즈 · {current_direction_name}':current_status_record['video'].rsplit('/',1)[0]+'/'+current_video_name for current_direction_name,current_video_name in current_result_record['dwpose_videos'].items()})
            current_status_record['reference_analysis_only']=current_result_record.get('reference_analysis_only',False)
            current_status_record['openpose_scale_percent'] = current_result_record.get('openpose_scale_percent',100.0)
            current_status_record['reference_proportions'] = current_result_record.get('reference_proportions',False)
            current_reference_record_path=current_job_root/'attempts'/current_result_record['attempt']/'reference-proportions.json'
            if current_reference_record_path.is_file():
                current_reference_record=json.loads(current_reference_record_path.read_text())
                current_status_record['reference_observation_count']=current_reference_record.get('observation_count',current_reference_record.get('image_count',0))
            current_status_record['remove_horizontal_motion'] = current_result_record.get('remove_horizontal_motion',False)
            current_comparison_path = current_job_root/'attempts'/current_result_record['attempt']/'comparison.mp4'
            if current_comparison_path.is_file() and current_comparison_path.resolve().is_relative_to(current_job_root.resolve()):
                current_pose_record_path = current_comparison_path.parent/'soma-pose.json'
                if current_pose_record_path.is_file():
                    current_status_record['pose_schema'] = json.loads(current_pose_record_path.read_text())['schema_version']
                current_status_record['pose_source'] = 'soma' if (current_comparison_path.parent/'soma-pose.json').is_file() else 'anny'
                current_status_record['comparison_video'] = current_status_record['video'].removesuffix('preview.mp4')+'comparison.mp4'
        return current_status_record
