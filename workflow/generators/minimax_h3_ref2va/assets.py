"""Ref2VA 가중치와 고정된 공식 구성의 준비 상태."""
from pathlib import Path
from generators.minimax_h3.assets import FILES, current_files
from workflow.generators.minimax_h3_ref2va.contracts import ROOT, PYTHON
from workflow.common.model_storage_layout import resolve_minimax_snapshot

REF = ROOT / '.model/minimax-h3-ref2va'
PIPELINE = ROOT / '.local/minimax-h3-ref2va/pipeline-config'
SNAPSHOT = resolve_minimax_snapshot(ROOT / '.model')
REF_FILES = [
    (REF / 'diffusion_models/minimax_h3_ref2va_pruned_fp8_scaled.safetensors', 20958205608, 'f86f2f79ebd2d76eb8eeb46091e83982e6ff51d255747e7b16e92834b392b8e9'),
    (REF / 'minimax_h3_ref2v_turbo_8step_v1.0_768p_bf16.safetensors', 1383677808, '9bac880b1a5d7ac052171cf6cce769f0cceaaa42ffa51de4b8e41143a2bdd2d2'),
]


def inspect_runtime():
    missing = []
    try:
        records = current_files(FILES)
    except ValueError as error:
        return {'ready': False, 'missing': [str(error)], 'message': '준비 필요: ' + str(error)}
    for path, size, _digest in [*records[1:6], *REF_FILES]:
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
            missing.append(path.name)
    for path in (PYTHON, SNAPSHOT / 'modular_model_index.json',
                 SNAPSHOT / 'tokenizer/tokenizer.json', SNAPSHOT / 'processor/preprocessor_config.json',
                 SNAPSHOT / 'scheduler/scheduler_config.json', SNAPSHOT / 'audio_scheduler/scheduler_config.json',
                 REF / 'transformer_ref/config.json', ROOT / '.local/minimax-h3-diffusers/deps/diffusers/__init__.py',
                 ROOT / '.local/minimax-h3-diffusers/deps/accelerate/__init__.py',
                 ROOT / '.local/minimax-h3-diffusers/deps/torchao/__init__.py',
                 ROOT / '.local/minimax-h3-diffusers/backend/core/inference/diffusion_comfy_quant.py',
                 ROOT / '.local/minimax-h3-diffusers/backend/core/inference/video_minimax_h3_te.py'):
        if not path.is_file():
            missing.append(path.name)
    try:
        if (ROOT / '.local/minimax-h3-diffusers/UNSLOTH_REVISION').read_text().strip() != 'e9e031d2fabec27d62269623737fbc0ba611862c':
            missing.append('변환 로더 리비전')
    except OSError:
        missing.append('변환 로더 리비전')
    return {'ready': not missing, 'missing': missing,
            'message': 'Ref2VA 파일 준비 완료 · 실행 시 SHA-256 검증' if not missing else '준비 필요: ' + ', '.join(missing)}


def prepare_pipeline_config():
    """고정 스냅샷의 구성 파일만 복사한다. 모델 가중치나 임시 실험에 의존하지 않는다."""
    import errno
    import filecmp
    import shutil
    import tempfile
    PIPELINE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='config-', dir=PIPELINE.parent) as tmp:
        staging = Path(tmp) / 'pipeline-config'
        staging.mkdir()
        for name in ('modular_model_index.json', 'model_index.json'):
            shutil.copyfile(SNAPSHOT / name, staging / name)
        for directory in ('text_encoder', 'tokenizer', 'processor', 'transformer', 'scheduler', 'audio_scheduler', 'vae', 'audio_vae'):
            target = staging / directory
            target.mkdir()
            for source in (SNAPSHOT / directory).iterdir():
                if source.is_file() and source.suffix in ('.json', '.txt'):
                    shutil.copyfile(source, target / source.name)
        (staging / 'transformer_ref').mkdir()
        shutil.copyfile(REF / 'transformer_ref/config.json', staging / 'transformer_ref/config.json')
        expected = [path.relative_to(staging) for path in staging.rglob('*') if path.is_file()]
        # 다른 실행 중 구성 경로를 교체하지 않는다. 동일한 공식 리비전 캐시는 재사용한다.
        try:
            staging.rename(PIPELINE)
        except OSError as error:
            if error.errno not in (errno.EEXIST, errno.ENOTEMPTY) or not PIPELINE.is_dir():
                raise
            for relative in expected:
                cached = PIPELINE / relative
                if cached.is_symlink() or not cached.is_file() or not filecmp.cmp(staging / relative, cached, shallow=False):
                    raise ValueError(f'Ref2VA 구성 캐시가 고정 모델 구성과 다릅니다: {relative}')
    return PIPELINE
