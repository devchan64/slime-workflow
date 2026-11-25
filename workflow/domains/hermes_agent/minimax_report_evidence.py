"""MiniMax 결과의 실제 파일과 실행 시도를 읽기 전용으로 검증한다."""
import hashlib
import json
import re
from pathlib import Path
from PIL import Image

SERVICES = frozenset(('minimax-h3-image', 'minimax-h3-i2v'))


def _read_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4_000_000:
        raise ValueError('작업 기록을 확인할 수 없습니다.')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('작업 기록 형식 오류')
    return value


def _file_info(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('결과 파일을 확인할 수 없습니다.')
    with path.open('rb') as stream:
        return {'sha256': hashlib.file_digest(stream, 'sha256').hexdigest(), 'size_bytes': path.stat().st_size}


def _image_info(path):
    info = _file_info(path)
    with Image.open(path, formats=['PNG']) as image:
        image.load()
        info['dimensions'] = list(image.size)
    return info


def inspect_minimax_result(directory, service):
    """고정된 출력과 표본 프레임을 검사한다. 시각적 품질은 판정하지 않는다."""
    directory = Path(directory)
    if service not in SERVICES or directory.is_symlink() or not directory.is_dir():
        raise ValueError('MiniMax 작업 경로 오류')
    status = _read_json(directory / 'status.json')
    if status.get('status') != 'completed':
        raise ValueError('완료된 작업이 아닙니다.')
    request = _read_json(directory / 'request.json')
    evidence = {'service': service, 'job_id': directory.name,
                'user_prompt': request.get('user_prompt', request.get('prompt')),
                'generation_prompt': request.get('prompt'),
                'settings': {key: request[key] for key in ('width', 'height', 'frames', 'steps', 'seed') if key in request}}
    if service == 'minimax-h3-image':
        if request.get('references'):
            from workflow.domains.image.three_reference_generation import verify_reference_snapshots
            verify_reference_snapshots(directory, request)
            evidence['references'] = [_image_info(directory/name) for name in request['references']]
        evidence['image'] = _image_info(directory / 'result.png')
        metadata = _read_json(directory / 'result.json')
        if metadata.get('image_sha256') != evidence['image']['sha256']:
            raise ValueError('이미지 결과 해시가 일치하지 않습니다.')
        evidence['actual_settings'] = {key: metadata[key] for key in ('width', 'height', 'steps', 'seed') if key in metadata}
        expected = [request.get('width'), request.get('height')]
        evidence['checks'] = {'png_decode':'pass', 'recorded_sha256':'pass', 'dimensions': ('pass' if evidence['image']['dimensions'] == expected else 'fail') if all(type(value) is int for value in expected) else 'unknown'}
        keys = ('width', 'height', 'steps', 'seed')
        evidence['checks']['recorded_settings_match'] = ('pass' if all(request[key] == metadata[key] for key in keys) else 'fail') if all(type(request.get(key)) is int and type(metadata.get(key)) is int for key in keys) else 'unknown'
        evidence['recorded_settings_note'] = '실행 결과 설정은 작업자가 요청값에서 기록한 값이며 독립적인 추론 설정 계측은 아닙니다.'
        evidence['result_url'] = f'/{service}/jobs/{directory.name}/result.png'
        return evidence
    from workflow.domains.image.three_reference_generation import verify_reference_snapshots
    verify_reference_snapshots(directory, request)
    if request.get('references') != ['reference-1.png']:
        raise ValueError('첫 프레임 참조를 확인할 수 없습니다.')
    evidence['reference'] = _image_info(directory / 'reference-1.png')
    pointer = _read_json(directory / 'current-attempt.json')
    attempt = pointer.get('id')
    if not isinstance(attempt, str) or not re.fullmatch(r'[a-f0-9]{32}', attempt) or status.get('attempt') != attempt:
        raise ValueError('완료된 영상 실행 시도를 확인할 수 없습니다.')
    attempts = directory / 'attempts'
    attempt_path = attempts / attempt
    if attempts.is_symlink() or attempt_path.is_symlink() or not attempt_path.is_dir():
        raise ValueError('영상 실행 시도 경로 오류')
    result = _read_json(attempt_path / 'result.json')
    frames = result.get('frames')
    fps = result.get('fps')
    if type(frames) is not int or not 1 <= frames <= 10000 or type(fps) not in (int, float) or not 0 < fps <= 240:
        raise ValueError('영상 프레임 기록 오류')
    video = _file_info(attempt_path / 'preview.mp4')
    if result.get('video_sha256') and video['sha256'] != result['video_sha256']:
        raise ValueError('영상 결과 해시가 일치하지 않습니다.')
    samples = []
    for index in sorted({0, (frames - 1) // 2, frames - 1}):
        info = _image_info(attempt_path / f'output-{index:03d}.png')
        hashes = result.get('output_sha256')
        if isinstance(hashes, list) and (index >= len(hashes) or info['sha256'] != hashes[index]):
            raise ValueError('영상 표본 프레임 해시가 일치하지 않습니다.')
        samples.append({'frame': index, 'seconds': index / fps, **info})
    expected = [request.get('width'), request.get('height')]
    checks = {'sample_png_decode':'pass', 'recorded_video_sha256':'pass' if result.get('video_sha256') else 'unknown',
              'sample_dimensions': ('pass' if all(item['dimensions'] == expected for item in samples) else 'fail') if all(type(value) is int for value in expected) else 'unknown',
              'recorded_frame_count': ('pass' if frames == request['frames'] else 'fail') if type(request.get('frames')) is int else 'unknown',
              'mp4_decode':'unknown'}
    evidence.update(attempt=attempt, frames=frames, fps=fps, video=video, samples=samples, checks=checks,
                    result_url=f'/{service}/jobs/{directory.name}/attempts/{attempt}/preview.mp4',
                    sampling_note='파일 무결성 검사의 표본은 합성 전 PNG입니다. 최종 MP4 디코딩과 시각 관찰은 별도 관찰 목록에서 확인해야 합니다.')
    audio = attempt_path / 'audio.wav'
    evidence['audio'] = _file_info(audio) if audio.is_file() and not audio.is_symlink() else None
    if evidence['audio']:
        evidence['audio']['scope'] = '생성된 audio.wav이며 최종 MP4 오디오 스트림은 별도 확인하지 않았습니다.'
        import wave
        try:
            with wave.open(str(audio), 'rb') as stream:
                rate = stream.getframerate()
                evidence['audio'].update(sample_rate=rate, channels=stream.getnchannels(),
                                         duration_seconds=stream.getnframes()/rate if rate else None)
        except (wave.Error, EOFError, OSError):
            evidence['audio']['duration_seconds'] = None
            evidence['audio']['note'] = '오디오 길이를 확인할 수 없습니다.'
    return evidence


def observe_minimax_result(directory, evidence, *, runner=None, lock_fd=None, memory_reader=None):
    """최종 결과의 CPU 시각 관찰을 생성하고 실패는 확인 불가로 기록한다."""
    import subprocess
    import tempfile
    root = Path(__file__).resolve().parents[3]
    runner = runner or subprocess.run
    service = evidence.get('service')
    if service not in SERVICES or inspect_minimax_result(directory, service) != evidence:
        raise ValueError('시각 관찰 전에 결과가 변경됐습니다.')
    directory = Path(directory)
    if memory_reader is None:
        from workflow.common.host_memory_guard import read_memory_field_kib
        memory_reader = lambda: read_memory_field_kib('/proc/meminfo', 'MemAvailable')
    def ensure_memory():
        if memory_reader() < 10 * 1024 * 1024:
            raise RuntimeError('시각 분석에 필요한 시스템 메모리 여유가 부족해 대기 중입니다.')
    def run(args, timeout):
        # GPU 작업과 함께 실행되는 CPU 검수는 낮은 우선순위로 실행한다.
        nice = Path('/usr/bin/nice')
        command = [str(nice), '-n', '10', *args] if nice.is_file() else args
        return runner(command, capture_output=True, text=True, check=True, timeout=timeout,
                      **({'pass_fds': lock_fd if isinstance(lock_fd, tuple) else (lock_fd,)} if lock_fd is not None else {}))
    observations = []
    with tempfile.TemporaryDirectory(prefix='minimax-report-frames-') as temporary:
        if service == 'minimax-h3-image':
            targets = [({'source':'result_image','seconds':None}, directory / 'result.png', evidence['image']['sha256'])]
            for index, reference in enumerate(evidence.get('references', []), start=1):
                targets.append(({'source':'reference_comparison', 'reference_index':index,
                                 'reference_sha256':reference['sha256']}, directory / 'result.png', evidence['image']['sha256']))
        else:
            attempt = directory / 'attempts' / evidence['attempt']
            targets = [({'source':'reference','seconds':None}, directory / 'reference-1.png', evidence['reference']['sha256'])]
            ensure_memory()
            try:
                result = run([str(root / '.venv/bin/python'), str(root / 'workflow/domains/hermes_agent/minimax_video_samples.py'),
                              str(attempt / 'preview.mp4'), evidence['video']['sha256'], temporary], 200)
                decoded = json.loads(result.stdout)
                samples = decoded['samples']
                if not isinstance(samples, list) or not 1 <= len(samples) <= 3:
                    raise ValueError('최종 영상 표본 목록 오류')
                for sample in samples:
                    filename, digest = sample['filename'], sample['sha256']
                    if (not isinstance(filename, str) or not re.fullmatch(r'sample-[0-9]{5}\.png', filename)
                            or not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)):
                        raise ValueError('최종 영상 표본 기록 오류')
                    path = Path(temporary) / filename
                    if _file_info(path)['sha256'] != digest:
                        raise ValueError('최종 영상 표본 해시 오류')
                    targets.append(({'source':'final_video','seconds':sample['seconds'],'frame':sample['frame'],
                                     'video_frames':decoded['frames'],'video_duration_seconds':decoded['duration_seconds'],
                                     'video_fps':decoded['fps'],'video_dimensions':decoded['dimensions'],
                                     'time_basis':'프레임 번호와 평균 FPS로 계산한 추정 시각'}, path, digest))
            except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError):
                observations.append({'source':'final_video','unavailable':'최종 MP4를 디코딩해 표본을 추출할 수 없습니다.'})
        for marker, path, digest in targets:
            ensure_memory()
            try:
                args = [str(root / '.venv/bin/python'), str(root / 'workflow/domains/image/flux_visual_review.py'), str(path), digest]
                if marker['source'] == 'reference_comparison':
                    args.extend([str(directory / f"reference-{marker['reference_index']}.png"), marker['reference_sha256']])
                result = run(args, 180)
                observation = json.loads(result.stdout)
                if not isinstance(observation, dict) or observation.get('image_sha256') != digest or not isinstance(observation.get('observation'), str):
                    raise ValueError('시각 관찰 응답 오류')
            except (OSError, subprocess.SubprocessError, ValueError, TypeError):
                observation = {'unavailable': '시각 모델 실행 실패 또는 응답 확인 불가', 'image_sha256': digest}
            observations.append({**marker, **observation})
    if inspect_minimax_result(directory, service) != evidence:
        raise ValueError('시각 관찰 중 결과가 변경됐습니다.')
    return observations
