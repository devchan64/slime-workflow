"""생성기 사용설명의 명시적 도메인 원본."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATOR_USAGE_PATHS = {
    'wan22-animate2': ROOT / 'generators/wan_animate2/README.md',
    'wan22-vace': ROOT / 'generators/wan_vace/README.md',
    'minimax-h3-i2v': ROOT / 'generators/minimax_h3/README.md',
    'minimax-h3-ref2va': ROOT / 'workflow/generators/minimax_h3_ref2va/README.md',
    'minimax-h3-building': ROOT / 'generators/minimax_h3_building/README.md',
    'minimax-h3-image': ROOT / 'generators/minimax_h3_image/README.md',
    'wan22-i2v': ROOT / 'generators/wan_i2v/README.md',
    'wan21-t2v': ROOT / 'generators/wan21_t2v/README.md',
    'wan21-i2v': ROOT / 'generators/wan21_i2v/README.md',
    'kimodo': ROOT / 'generators/kimodo/README.md',
}

def read_generator_usage(generator):
    path = GENERATOR_USAGE_PATHS.get(generator)
    if path is None:
        raise ValueError('등록되지 않은 생성기입니다.')
    try:
        return path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as error:
        raise OSError('사용설명을 읽을 수 없습니다. 생성기 README.md와 읽기 권한을 확인하세요.') from error
