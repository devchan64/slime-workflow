"""등록 에셋에서 격리 출판 검사에 쓸 합성 원장 입력을 만든다."""
import argparse
import json
from pathlib import Path

from workflow.domains.map_assets.database_seed import build_billboard_database_seed, build_map_database_seed
from workflow.maintenance.sync_billboard_catalog import load_unique_yaml_document


def build_synthetic_ledger_fixture(current_asset_root):
    """DB에 연결하지 않고 현재 원본에 근거한 시험 자료를 반환한다."""
    current_asset_root=Path(current_asset_root).resolve(strict=True)
    current_billboard_seed=build_billboard_database_seed(current_asset_root,'/assets')
    current_map_seed=build_map_database_seed(current_asset_root)
    return {'schemaVersion':1,'generation':1,'types':current_billboard_seed['types'],
            'assets':[{**current_asset,'revision':1,'retired':False} for current_asset in current_billboard_seed['assets']],
            'mapDocuments':current_map_seed['documents'],
            'mapRevisions':{current_path:1 for current_path in current_map_seed['documents']},
            'buildingProperties':current_map_seed['buildingProperties'],
            'effects':load_unique_yaml_document(current_asset_root/'assets/sprites/effects/catalog.yaml')['effects']}


def main_asset_fixture_builder():
    current_parser=argparse.ArgumentParser(description=__doc__)
    current_parser.add_argument('--asset-root',required=True,help='읽기 전용 에셋 저장소')
    current_parser.add_argument('--output',required=True,help='합성 원장 JSON 경로')
    current_arguments=current_parser.parse_args()
    current_output_path=Path(current_arguments.output)
    current_asset_root=Path(current_arguments.asset_root).resolve(strict=True)
    if current_output_path.resolve().is_relative_to(current_asset_root):
        raise ValueError('시험 자료를 에셋 원본 저장소에 기록할 수 없습니다.')
    current_fixture=build_synthetic_ledger_fixture(current_asset_root)
    with current_output_path.open('x',encoding='utf-8') as current_stream:
        json.dump(current_fixture,current_stream,ensure_ascii=False)


if __name__=='__main__':
    main_asset_fixture_builder()
