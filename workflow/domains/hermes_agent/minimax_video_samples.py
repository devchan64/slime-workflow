"""최종 MP4를 CPU로 디코딩해 시작·중간·끝 표본을 격리 폴더에 기록한다."""
import hashlib
import json
import sys
from pathlib import Path


def extract(video, expected_hash, output_directory):
    import imageio_ffmpeg
    from PIL import Image
    video = Path(video)
    output_directory = Path(output_directory)
    if video.is_symlink() or not video.is_file() or output_directory.is_symlink() or not output_directory.is_dir():
        raise ValueError('영상 또는 표본 경로를 확인할 수 없습니다.')
    with video.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected_hash:
            raise ValueError('영상 해시가 일치하지 않습니다.')
    import subprocess
    metadata = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-hide_banner', '-loglevel', 'error',
                               '-i', str(video), '-map', '0:v:0', '-progress', 'pipe:1', '-nostats',
                               '-f', 'null', '-'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    fields = {}
    for line in metadata.stdout.decode('utf-8', errors='replace').splitlines():
        key, separator, value = line.partition('=')
        if separator: fields[key] = value.strip()
    try:
        count = int(fields['frame'])
        duration = int(fields['out_time_us']) / 1_000_000
    except (KeyError, ValueError) as error:
        raise ValueError('영상 디코딩 정보를 확인할 수 없습니다.') from error
    if not 1 <= count <= 10000 or not 0 < duration <= 3600:
        raise ValueError('영상 길이 또는 프레임 수 오류')
    indexes = sorted({0, (count-1)//2, count-1})
    pattern = output_directory / 'decoded-%02d.png'
    expression = '+'.join(f'eq(n\\,{index})' for index in indexes)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-hide_banner', '-loglevel', 'error',
                    '-i', str(video), '-vf', 'select='+expression, '-fps_mode', 'passthrough',
                    '-frames:v', str(len(indexes)), str(pattern)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=90)
    samples = []
    dimensions = None
    for order, index in enumerate(indexes, 1):
        source = output_directory / f'decoded-{order:02d}.png'
        if source.is_symlink() or not source.is_file():
            raise ValueError('최종 영상 표본 디코딩이 불완전합니다.')
        with Image.open(source, formats=['PNG']) as image:
            image.load()
            if image.width <= 0 or image.height <= 0 or image.width*image.height > 16_777_216:
                raise ValueError('영상 해상도 오류')
            if dimensions is not None and dimensions != list(image.size):
                raise ValueError('영상 표본 해상도 불일치')
            dimensions = list(image.size)
        path = output_directory / f'sample-{index:05d}.png'
        source.rename(path)
        samples.append({'frame':index,'seconds':index*duration/count,'filename':path.name,
                        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    fps = count / duration
    with video.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected_hash:
            raise ValueError('영상 디코딩 중 결과가 변경됐습니다.')
    return {'frames':count,'duration_seconds':duration,'fps':fps,'dimensions':dimensions,'samples':samples}


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('영상 경로·해시·출력 폴더가 필요합니다.')
    print(json.dumps(extract(sys.argv[1],sys.argv[2],sys.argv[3]),ensure_ascii=False))
