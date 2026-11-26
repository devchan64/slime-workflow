"""오디오 실행 환경과 분리된 고정 모델 파일 다운로드."""
import fcntl
import json
import os
from pathlib import Path

from generators.music.contracts import resolve_music_paths
from workflow.common.generation_records import write_record_atomically

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
AUDIO_DOWNLOAD_PROFILES = {'music-heartmula': 'heartmula-model', 'sfx-dasheng-audiogen': 'dasheng-model'}


def resolve_audio_receipt_file(service, model_root, relative_name):
    """Resolve a recorded relative file without allowing path escape."""
    relative = Path(relative_name)
    if relative.is_absolute() or not relative.parts or any(part in ('.', '..') for part in relative.parts):
        raise ValueError('오디오 준비 기록 경로가 올바르지 않습니다.')
    if service == 'music-heartmula' and relative.parts[0] == 'demucs':
        from generators.music.heartmula.separation import resolve_demucs_directory
        base = resolve_demucs_directory(model_root)
        file_path = base.joinpath(*relative.parts[1:])
    elif service == 'sfx-dasheng-audiogen':
        from generators.sound_effects.runtime import resolve_effects_file
        return resolve_effects_file(model_root, relative)
    elif service == 'music-heartmula' and len(relative.parts) >= 2 and relative.parts[:2] in (('bundle', 'HeartCodec-oss'), ('bundle', 'HeartMuLa-oss-3B')):
        from generators.music.heartmula.runtime import resolve_heart_component
        base = resolve_heart_component(model_root, relative.parts[1])
        file_path = base.joinpath(*relative.parts[2:])
    elif service == 'music-heartmula' and relative.parts[0] == 'bundle':
        from generators.music.heartmula.runtime import resolve_heart_bundle
        base = resolve_heart_bundle(model_root)
        file_path = base.joinpath(*relative.parts[1:])
    else:
        base = model_root
        file_path = base / relative
    if file_path.is_symlink() or not file_path.resolve().is_relative_to(base.resolve()):
        raise ValueError('오디오 준비 기록이 모델 경로 밖을 가리킵니다.')
    return file_path


def resolve_audio_download_sources(current_service_name):
    if current_service_name == 'music-heartmula':
        from generators.music.heartmula.runtime import HEARTMULA_SOURCE_REVISIONS
        return HEARTMULA_SOURCE_REVISIONS
    if current_service_name == 'sfx-dasheng-audiogen':
        from generators.sound_effects.runtime import DASHENG_MODEL_REVISIONS
        return DASHENG_MODEL_REVISIONS
    raise ValueError('지원하지 않는 오디오 모델입니다.')


def validate_dasheng_required_files(model_root, sources, receipt_files=None):
    from generators.sound_effects.runtime import resolve_effects_component
    from workflow.common.model_offline_audio_check import REQUIRED
    component_names = {'model': 'dasheng-audiogen', 'text-encoder': 'flan-t5-large',
                       'audio-tokenizer': 'dasheng-tokenizer'}
    for _, _, component in sources:
        model = component_names.get(component)
        if model is None:
            raise ValueError('알 수 없는 Dasheng 모델 구성요소입니다: ' + component)
        component_root = resolve_effects_component(model_root, component)
        for relative in REQUIRED['sfx-dasheng-audiogen'][model]:
            path = component_root / relative
            if (receipt_files is not None and f'{component}/{relative}' not in receipt_files):
                raise ValueError('Dasheng 준비 기록에 필수 파일이 없습니다: ' + relative)
            if (component_root.is_symlink() or path.is_symlink() or not path.is_file()
                    or not path.resolve().is_relative_to(component_root.resolve()) or path.stat().st_size == 0):
                raise ValueError('Dasheng 필수 모델 파일이 없거나 비어 있습니다: ' + relative)


def validate_heartmula_required_files(model_root, receipt_files=None):
    from generators.music.heartmula.separation import DEMUCS_CHECKPOINT_NAME

    def required(name):
        if receipt_files is not None and name not in receipt_files:
            raise ValueError('HeartMuLa 준비 기록에 필수 파일이 없습니다: ' + name)
        path = resolve_audio_receipt_file('music-heartmula', model_root, name)
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError('HeartMuLa 필수 모델 파일이 없거나 비어 있습니다: ' + name)
        return path

    for name in ('bundle/tokenizer.json', 'bundle/gen_config.json', 'demucs/' + DEMUCS_CHECKPOINT_NAME):
        required(name)
    for component in ('HeartMuLa-oss-3B', 'HeartCodec-oss'):
        prefix = 'bundle/' + component + '/'
        required(prefix + 'config.json')
        index = required(prefix + 'model.safetensors.index.json')
        if index.stat().st_size > 16 * 1024 * 1024:
            raise ValueError('HeartMuLa 가중치 목록이 너무 큽니다.')
        index_data = json.loads(index.read_text(encoding='utf-8'))
        weights = index_data.get('weight_map') if isinstance(index_data, dict) else None
        if not isinstance(weights, dict) or not weights or any(not isinstance(name, str) or not name for name in weights.values()):
            raise ValueError('HeartMuLa 가중치 목록이 올바르지 않습니다.')
        for name in set(weights.values()):
            required(prefix + name)


def inspect_audio_download_files(current_service_name):
    """다운로드한 파일이 완료 확인 이후 바뀌지 않았는지 확인한다."""
    current_profile_name = AUDIO_DOWNLOAD_PROFILES[current_service_name]
    current_model_root = resolve_music_paths(current_service_name)[1]
    current_receipt_path = WORKFLOW_ROOT_DIRECTORY/'.local/model-preparation'/current_profile_name/'files.json'
    try:
        current_receipt_record = json.loads(current_receipt_path.read_text())
        if current_receipt_record['sources'] != [list(current_source) for current_source in resolve_audio_download_sources(current_service_name)]:
            return False
        current_files_record = current_receipt_record['files']
        if not isinstance(current_files_record, dict) or not current_files_record:
            return False
        if current_service_name == 'sfx-dasheng-audiogen':
            validate_dasheng_required_files(current_model_root, resolve_audio_download_sources(current_service_name), current_files_record)
        elif current_service_name == 'music-heartmula':
            validate_heartmula_required_files(current_model_root, current_files_record)
        for current_relative_name, current_file_record in current_files_record.items():
            current_file_path = resolve_audio_receipt_file(current_service_name, current_model_root, current_relative_name)
            if not current_file_path.is_file():
                return False
            current_file_stat = current_file_path.stat()
            if current_file_record != [current_file_stat.st_size, current_file_stat.st_mtime_ns, current_file_stat.st_ctime_ns]:
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def download_audio_model_files(current_service_name):
    """고정 리비전 파일만 공용 다운로더로 받으며 GPU를 사용하지 않는다."""
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    import huggingface_hub.constants as current_hub_constants
    current_hub_constants.HF_HUB_DISABLE_XET = True
    from workflow.common.model_huggingface_download import tracked_snapshot_download
    current_model_root = resolve_music_paths(current_service_name)[1]
    current_model_root.mkdir(parents=True, exist_ok=True)
    with (current_model_root/'prepare.lock').open('a') as current_lock_stream:
        fcntl.flock(current_lock_stream, fcntl.LOCK_EX)
        current_source_records = resolve_audio_download_sources(current_service_name)
        for current_repository_name, current_revision_value, current_directory_name in current_source_records:
            current_destination = current_model_root/current_directory_name
            if current_service_name == 'music-heartmula' and current_directory_name in ('bundle/HeartCodec-oss', 'bundle/HeartMuLa-oss-3B'):
                from generators.music.heartmula.runtime import resolve_heart_component
                current_destination = resolve_heart_component(current_model_root, Path(current_directory_name).name)
            elif current_service_name == 'music-heartmula' and current_directory_name == 'bundle':
                from generators.music.heartmula.runtime import resolve_heart_bundle
                current_destination = resolve_heart_bundle(current_model_root)
            elif current_service_name == 'sfx-dasheng-audiogen':
                from generators.sound_effects.runtime import resolve_effects_component
                current_destination = resolve_effects_component(current_model_root, current_directory_name)
            current_download_options = {'repo_id': current_repository_name, 'revision': current_revision_value,
                                        'local_dir': str(current_destination)}
            if current_service_name == 'sfx-dasheng-audiogen':
                current_download_options['allow_patterns'] = ['*.json', '*.py', '*.safetensors', '*.model', '*.txt', 'README.md', 'LICENSE*']
            tracked_snapshot_download(**current_download_options)
        if current_service_name == 'sfx-dasheng-audiogen':
            validate_dasheng_required_files(current_model_root, current_source_records)
        if current_service_name == 'music-heartmula':
            from generators.music.heartmula.separation import prepare_separation_model
            prepare_separation_model(current_model_root, True)
            from generators.music.heartmula.runtime import resolve_heart_bundle
            current_bundle_root = resolve_heart_bundle(current_model_root)
            for current_required_name in ('tokenizer.json', 'gen_config.json'):
                if not (current_bundle_root/current_required_name).is_file():
                    raise ValueError('HeartMuLa 필수 모델 파일이 없습니다: ' + current_required_name)
            for current_component_name in ('HeartMuLa-oss-3B', 'HeartCodec-oss'):
                from generators.music.heartmula.runtime import resolve_heart_component
                current_component_root = resolve_heart_component(current_model_root,current_component_name)
                current_index_record = json.loads((current_component_root/'model.safetensors.index.json').read_text())
                current_weight_map = current_index_record['weight_map']
                if not isinstance(current_weight_map, dict) or not current_weight_map:
                    raise ValueError('HeartMuLa 가중치 목록이 비어 있습니다: ' + current_component_name)
                for current_shard_name in set(current_weight_map.values()):
                    current_shard_path = current_component_root/current_shard_name
                    if (not current_shard_path.resolve().is_relative_to(current_component_root.resolve()) or
                            current_shard_path.is_symlink() or not current_shard_path.is_file() or not current_shard_path.stat().st_size):
                        raise ValueError('HeartMuLa 가중치 파일이 없거나 올바르지 않습니다: ' + str(current_shard_name))
            validate_heartmula_required_files(current_model_root)
        current_file_records = {}
        current_source_paths = [current_model_root/current_source[2] for current_source in current_source_records]
        if current_service_name == 'music-heartmula':
            from generators.music.heartmula.runtime import resolve_heart_component, resolve_heart_bundle
            current_source_paths = [resolve_heart_component(current_model_root,Path(source[2]).name) if source[2] in ('bundle/HeartCodec-oss','bundle/HeartMuLa-oss-3B') else resolve_heart_bundle(current_model_root) if source[2] == 'bundle' else path for source, path in zip(current_source_records, current_source_paths)]
        elif current_service_name == 'sfx-dasheng-audiogen':
            from generators.sound_effects.runtime import resolve_effects_component
            current_source_paths = [resolve_effects_component(current_model_root, source[2]) for source in current_source_records]
        if current_service_name == 'music-heartmula':
            from generators.music.heartmula.separation import resolve_demucs_directory
            current_source_paths.append(resolve_demucs_directory(current_model_root))
        for current_source_index, current_source_path in enumerate(current_source_paths):
            current_source_count = 0
            for current_file_path in current_source_path.rglob('*'):
                if (not current_file_path.is_file() or current_file_path.is_symlink() or
                        not current_file_path.resolve().is_relative_to(current_source_path.resolve()) or
                        any(current_part.startswith('.') for current_part in current_file_path.relative_to(current_source_path).parts) or
                        current_file_path.name.endswith(('.partial', '.verified', '.incomplete', '.lock', '.tmp'))):
                    continue
                current_file_stat = current_file_path.stat()
                if current_service_name == 'music-heartmula' and current_source_path == resolve_demucs_directory(current_model_root):
                    receipt_name = (Path('demucs') / current_file_path.relative_to(current_source_path)).as_posix()
                elif current_service_name == 'sfx-dasheng-audiogen':
                    receipt_name = (Path(current_source_records[current_source_index][2]) / current_file_path.relative_to(current_source_path)).as_posix()
                elif current_service_name == 'music-heartmula' and current_source_index < len(current_source_records) and current_source_records[current_source_index][2] in ('bundle','bundle/HeartCodec-oss','bundle/HeartMuLa-oss-3B'):
                    receipt_name = (Path(current_source_records[current_source_index][2]) / current_file_path.relative_to(current_source_path)).as_posix()
                else:
                    receipt_name = current_file_path.relative_to(current_model_root).as_posix()
                current_file_records[receipt_name] = [current_file_stat.st_size, current_file_stat.st_mtime_ns, current_file_stat.st_ctime_ns]
                current_source_count += 1
            if not current_source_count:
                raise ValueError('다운로드한 모델 구성 요소가 비어 있습니다: ' + current_source_path.name)
        if not current_file_records:
            raise ValueError('다운로드한 모델 파일이 없습니다.')
        current_receipt_path = WORKFLOW_ROOT_DIRECTORY/'.local/model-preparation'/AUDIO_DOWNLOAD_PROFILES[current_service_name]/'files.json'
        current_receipt_path.parent.mkdir(parents=True, exist_ok=True)
        write_record_atomically(current_receipt_path, {'sources': current_source_records, 'files': current_file_records})


def download_heartmula_model_files():
    download_audio_model_files('music-heartmula')


def download_dasheng_model_files():
    download_audio_model_files('sfx-dasheng-audiogen')
