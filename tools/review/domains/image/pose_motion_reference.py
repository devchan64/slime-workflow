"""등록된 걷기 모션의 ANNY 참조와 보조 문구를 읽는다."""
import hashlib
from pathlib import Path

import yaml
from tools.review.common.map_tile_assets import UniqueAssetYamlLoader
from PIL import Image

MOTION_REFERENCE_ROOT = Path(__file__).resolve().parents[4] / 'assets/motion-sheet/hy-motion-walking-v2'
MOTION_PROMPT_CONFIG = Path(__file__).resolve().parents[4] / 'generators/image/config/pose-motion-prompts.yaml'


def load_motion_reference(selected_direction_value, selected_frame_number):
    """1부터 시작하는 프레임 번호를 검증하고 해시가 일치하는 이미지를 반환한다."""
    current_manifest_record = yaml.safe_load((MOTION_REFERENCE_ROOT / 'manifest.yaml').read_text())
    if selected_direction_value not in current_manifest_record['directions']:
        raise ValueError('등록된 걷기 방향을 선택하세요.')
    if isinstance(selected_frame_number, bool) or not isinstance(selected_frame_number, (int, float)) or not float(selected_frame_number).is_integer() or not 1 <= selected_frame_number <= current_manifest_record['frames']:
        raise ValueError('걷기 프레임은 1~35 사이의 정수여야 합니다.')
    selected_frame_number = int(selected_frame_number)
    selected_relative_path = f'anny/{selected_direction_value}/anny-{selected_frame_number:04d}.png'
    selected_image_bytes = (MOTION_REFERENCE_ROOT / selected_relative_path).read_bytes()
    if hashlib.sha256(selected_image_bytes).hexdigest() != current_manifest_record['files'][selected_relative_path]:
        raise ValueError('걷기 ANNY 참조의 등록 해시가 일치하지 않습니다.')
    current_prompt_record = yaml.load(MOTION_PROMPT_CONFIG.read_text(), Loader=UniqueAssetYamlLoader)
    if set(current_prompt_record) != {'template', 'directions'} or not isinstance(current_prompt_record['template'], str) or set(current_prompt_record['directions']) != set(current_manifest_record['directions']) or not all(isinstance(current_direction_text, str) for current_direction_text in current_prompt_record['directions'].values()):
        raise ValueError('걷기 프리셋 보조 프롬프트 설정이 올바르지 않습니다.')
    selected_prompt_text = current_prompt_record['template'].format(direction=current_prompt_record['directions'][selected_direction_value])
    with Image.open(MOTION_REFERENCE_ROOT / selected_relative_path) as selected_image_value:
        loaded_image_value = selected_image_value.copy()
    source_frame_number = current_manifest_record['source_frames'][selected_frame_number-1]
    return loaded_image_value, selected_prompt_text, f'걷기 v2 · {selected_direction_value} · {selected_frame_number}/35 · 원본 {source_frame_number}번 · ANNY 참조 적용'


def find_matching_auxiliary(current_history_records, selected_pose_digest, current_base_prompt):
    """같은 참조의 완료 이력에서 기본 문구 뒤에 붙였던 보조 문구를 찾는다."""
    for current_history_record in sorted(current_history_records, key=lambda current_record_value: current_record_value['id'], reverse=True):
        current_request_record = current_history_record['request']
        current_snapshot_records = current_request_record.get('reference_snapshots', [])
        current_saved_prompt = current_request_record.get('prompt', '')
        if (current_history_record.get('status', {}).get('status') == 'completed'
                and len(current_snapshot_records) == 2
                and current_snapshot_records[1]['sha256'] == selected_pose_digest
                and current_saved_prompt.startswith(current_base_prompt + ' ')):
            return current_saved_prompt[len(current_base_prompt):].strip(), current_history_record['id']
    return None
