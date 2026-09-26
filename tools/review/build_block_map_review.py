"""명시적으로 내보낸 게임 블록 기하 사본을 관리도구에 게시한다."""
from pathlib import Path
import json
import shutil
import yaml

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[2]


def build_block_map_review(output_directory_path):
    output_directory_path=Path(output_directory_path).resolve()
    if not output_directory_path.is_relative_to(WORKFLOW_ROOT_DIRECTORY/'.tmp'):
        raise ValueError('검수 출력은 .tmp 하위여야 합니다.')
    source_asset_directory=WORKFLOW_ROOT_DIRECTORY/'assets/world/isloon/blocks'
    current_map_record=json.loads((source_asset_directory/'iseulon.json').read_text())
    if current_map_record['id']!='iseulon' or any(current_building_record['blockSchemaVersion']!=1 for current_building_record in current_map_record['buildings']):
        raise ValueError('이슬온 블록 스키마가 다릅니다.')
    current_material_record=yaml.safe_load((source_asset_directory/'materials.yaml').read_text())
    required_material_names=set(current_map_record['terrainCodes'].values())|{'wall','roof'}
    if required_material_names-set(current_material_record['materials']):
        raise ValueError('임시 재질이 정의되지 않았습니다.')
    output_directory_path.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source_asset_directory/'iseulon.json',output_directory_path/'block-map.json')
    (output_directory_path/'block-materials.json').write_text(json.dumps(current_material_record['materials']))
    source_ui_directory=WORKFLOW_ROOT_DIRECTORY/'tools/review/ui/map'
    shutil.copy2(source_ui_directory/'block-map-review.html',output_directory_path/'map-review.html')
    shutil.copy2(source_ui_directory/'block-map-review.js',output_directory_path/'block-map-review.js')
    return output_directory_path
