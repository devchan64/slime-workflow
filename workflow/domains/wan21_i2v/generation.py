"""Wan 2.1 I2V service isolated from the 2.2 generator."""
from generators.wan21_i2v.assets import DIRECTORY, FILES, ROOT, inspect_assets
from generators.wan21_i2v.worker import JOB_STORAGE
from generators.wan21_video_contracts import PYTHON, RUNTIME, validate_request
from generators.wan_i2v.contracts import COMFY_REVISION, SHARED_FILES
from workflow.common.reference_video_generation import ReferenceVideoGenerationManager


def inspect_runtime(verify_hash=False):
    missing=[]
    for path,size in SHARED_FILES:
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
                missing.append(str(path))
        except OSError:
            missing.append(str(path))
    if not PYTHON.is_file(): missing.append(str(PYTHON))
    try:
        if (RUNTIME/'PINNED_REVISION').read_text().strip() != COMFY_REVISION:
            missing.append('ComfyUI 고정 리비전 불일치')
    except OSError:
        missing.append('ComfyUI 고정 리비전 확인 불가')
    def sizes_ok():
        try:
            return all(not (DIRECTORY/p).is_symlink() and (DIRECTORY/p).is_file() and (DIRECTORY/p).stat().st_size==size for p,_,_,_,size,_ in FILES)
        except OSError:
            return False
    if not (inspect_assets() if verify_hash else sizes_ok()): missing.append('Wan 2.1 I2V 모델 및 LoRA')
    return {'ready':not missing,'missing':missing,'message':('파일 확인 완료 · GPU 실행과 품질 미검증' if not missing else '준비 필요: '+', '.join(missing))}


def validate_runtime():
    status=inspect_runtime()
    if not status['ready']: raise ValueError(status['message'])


class Wan21I2VGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan21-i2v',JOB_STORAGE,'generators/wan21_i2v/worker.py',lambda request: validate_request(request,'i2v'),validate_runtime,inspect_runtime)
    def select_generation_python(self,saved_request_record=None): return PYTHON
    def select_generation_service(self,saved_request_record=None): return 'wan21-i2v'
    def validate_generation_runtime(self,saved_request_record=None):
        validate_runtime()
        if saved_request_record and saved_request_record.get('action_lora') and saved_request_record.get('action_variant','fight') in ('attack_high','attack_low'):
            from generators.wan21_i2v.attack_lora import FILES as attack_files
            for relative,_,_,_,size,_ in attack_files:
                path=DIRECTORY/relative
                if path.is_symlink() or not path.is_file() or path.stat().st_size!=size:
                    raise ValueError('공격 동작 LoRA 파일을 먼저 준비하세요.')
    def hold_generation_submission_guard(self):
        from contextlib import ExitStack
        from workflow.common.model_prepare_process import hold_registered_preparation_guard
        stack=ExitStack()
        try:
            stack.enter_context(hold_registered_preparation_guard(ROOT,'wan21-i2v-assets'))
            stack.enter_context(hold_registered_preparation_guard(ROOT,'wan21-i2v-attack-lora'))
        except BaseException:
            stack.close()
            raise
        return stack
