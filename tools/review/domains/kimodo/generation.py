"""공용 대기열·누적 이력·실제 파일 삭제 계약을 사용하는 Kimodo 서비스."""
from generators.kimodo.contracts import KIMODO_JOB_STORAGE,inspect_kimodo_assets,validate_kimodo_assets,validate_kimodo_request
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager

class KimodoGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/kimodo',KIMODO_JOB_STORAGE,'generators/kimodo/worker.py',validate_kimodo_request,validate_kimodo_assets,inspect_kimodo_assets)

    def validate_generation_runtime(self,saved_request_record=None):
        super().validate_generation_runtime(saved_request_record)
        if saved_request_record and (saved_request_record.get('images') or saved_request_record.get('references')):
            from generators.kimodo.reference_extraction import validate_reference_pose_runtime
            validate_reference_pose_runtime()

    def validate_generation_resume(self,selected_job_directory):
        import json
        current_saved_request=json.loads((selected_job_directory/'request.json').read_text())
        if current_saved_request.get('action')=='reference-analysis':
            raise ValueError('참조 추출 검증은 모션 생성 재개 대상이 아닙니다. 참조 입력을 불러와 새 작업을 생성하세요.')
        self.validate_generation_runtime(current_saved_request)

    def read_generation_status_record(self,current_job_root,fallback_status_record=None,include_log_value=False):
        current_status_record = super().read_generation_status_record(current_job_root,fallback_status_record,include_log_value)
        if current_status_record.get('video'):
            import json
            current_result_record = json.loads((current_job_root/'result.json').read_text())
            if current_result_record.get('soma_render_videos'):
                current_status_record['preprocess_videos'] = {f'SOMA 렌더 · {current_direction_name}': current_status_record['video'].rsplit('/', 1)[0]+'/'+current_video_name for current_direction_name, current_video_name in current_result_record['soma_render_videos'].items()}
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
