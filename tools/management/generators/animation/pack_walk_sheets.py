#!/usr/bin/env python3
"""정규화된 384px 걷기 셀 32개를 픽셀 변경 없이 4×4 두 장으로 패킹한다."""
import argparse
import hashlib
import json
import logging
from pathlib import Path
from PIL import Image

WALK_DIRECTION_GROUPS = (('down_left', 'down_right'), ('up_left', 'up_right'))
FRAME_CELL_SIZE = 384
REFERENCE_BODY_HEIGHT = 288
GAME_CHARACTER_HEIGHT = 60
FRAME_DIRECTION_COUNT = 8
SHEET_GRID_LENGTH = 4


def calculate_file_digest(source_file_path):
    return hashlib.sha256(source_file_path.read_bytes()).hexdigest()


def pack_walk_frames(normalized_cell_root, packed_output_root):
    normalized_cell_root, packed_output_root = map(Path, (normalized_cell_root, packed_output_root))
    packed_output_root.mkdir(parents=True, exist_ok=False)
    run_output_logger = logging.getLogger('walk-pack.'+str(packed_output_root.resolve()))
    run_output_logger.setLevel(logging.INFO)
    run_output_logger.propagate = False
    for output_log_handler in (logging.FileHandler(packed_output_root/'execution.log'), logging.StreamHandler()):
        output_log_handler.setFormatter(logging.Formatter('%(asctime)s/walk-pack/%(message)s'))
        run_output_logger.addHandler(output_log_handler)
    try:
        normalized_record_values = json.loads((normalized_cell_root/'frames.json').read_text())
        expected_frame_identifiers = {f'{direction_key_name}.{frame_index_value}' for direction_pair_values in WALK_DIRECTION_GROUPS for direction_key_name in direction_pair_values for frame_index_value in range(FRAME_DIRECTION_COUNT)}
        actual_frame_identifiers = [frame_record_values['frameId'] for frame_record_values in normalized_record_values['frames']]
        if len(actual_frame_identifiers) != 32 or set(actual_frame_identifiers) != expected_frame_identifiers:
            raise ValueError('걷기 4방향×8프레임의 중복·누락을 확인하세요.')
        if {source_file_path.stem for source_file_path in normalized_cell_root.glob('*.png')} != expected_frame_identifiers:
            raise ValueError('프레임 PNG 목록과 메타데이터가 다릅니다.')
        packed_frame_records, packed_sheet_records = [], []
        for sheet_group_index, direction_pair_values in enumerate(WALK_DIRECTION_GROUPS):
            packed_sheet_image = Image.new('RGBA', (FRAME_CELL_SIZE*SHEET_GRID_LENGTH,)*2)
            packed_sheet_name = 'walk-'+('down' if sheet_group_index == 0 else 'up')+'.png'
            for direction_pair_index, direction_key_name in enumerate(direction_pair_values):
                for frame_index_value in range(FRAME_DIRECTION_COUNT):
                    target_frame_identifier = f'{direction_key_name}.{frame_index_value}'
                    source_frame_record = next(frame_record_values for frame_record_values in normalized_record_values['frames'] if frame_record_values['frameId'] == target_frame_identifier)
                    source_cell_path = normalized_cell_root/(target_frame_identifier+'.png')
                    selected_cell_image = Image.open(source_cell_path)
                    if selected_cell_image.mode != 'RGBA' or selected_cell_image.size != (FRAME_CELL_SIZE, FRAME_CELL_SIZE) or selected_cell_image.getchannel('A').getextrema() != (0,255):
                        raise ValueError(f'투명 RGBA 384×384 셀 필요: {target_frame_identifier}')
                    if calculate_file_digest(source_cell_path) != source_frame_record['sha256']:
                        raise ValueError(f'셀 해시 불일치: {target_frame_identifier}')
                    target_anchor_values = source_frame_record['anchor']
                    if set(target_anchor_values) != {'x','y'} or any(type(anchor_component_value) is not int or not 0 <= anchor_component_value < FRAME_CELL_SIZE for anchor_component_value in target_anchor_values.values()):
                        raise ValueError(f'정수 로컬 앵커 범위 오류: {target_frame_identifier}')
                    packed_cell_index = direction_pair_index*8+frame_index_value
                    target_cell_left, target_cell_top = packed_cell_index%SHEET_GRID_LENGTH*FRAME_CELL_SIZE, packed_cell_index//SHEET_GRID_LENGTH*FRAME_CELL_SIZE
                    packed_sheet_image.paste(selected_cell_image,(target_cell_left,target_cell_top))
                    if packed_sheet_image.crop((target_cell_left,target_cell_top,target_cell_left+FRAME_CELL_SIZE,target_cell_top+FRAME_CELL_SIZE)).tobytes() != selected_cell_image.tobytes():
                        raise RuntimeError('패킹 중 RGBA 값이 변경되었습니다.')
                    packed_frame_records.append({**source_frame_record,'texture':packed_sheet_name,'rect':{'x':target_cell_left,'y':target_cell_top,'width':FRAME_CELL_SIZE,'height':FRAME_CELL_SIZE}})
            packed_sheet_image.save(packed_output_root/packed_sheet_name)
            packed_sheet_records.append({'image':packed_sheet_name,'width':FRAME_CELL_SIZE*SHEET_GRID_LENGTH,'height':FRAME_CELL_SIZE*SHEET_GRID_LENGTH,'sha256':calculate_file_digest(packed_output_root/packed_sheet_name),'directions':list(direction_pair_values)})
            run_output_logger.info('sheet %s 16프레임 RGBA 보존 검증 완료',packed_sheet_name)
        animation_output_values = {'animationId':'character.default.white-shirt.walk','version':'3-candidate','referenceBodyHeight':REFERENCE_BODY_HEIGHT,'gameBodyHeight':GAME_CHARACTER_HEIGHT,'sheets':packed_sheet_records,'frames':packed_frame_records,'clips':normalized_record_values['clips']}
        (packed_output_root/'walk.animation.json').write_text(json.dumps(animation_output_values,ensure_ascii=False,indent=2)+'\n')
        (packed_output_root/'source.json').write_text(json.dumps({'state':'candidate-pending-review','runtimeAdopted':False,'layout':[4,4],'cellSize':[FRAME_CELL_SIZE,FRAME_CELL_SIZE],'normalization':normalized_record_values['normalization'],'normalizationManifest':str((normalized_cell_root/'frames.json').resolve()),'normalizationManifestSha256':calculate_file_digest(normalized_cell_root/'frames.json'),'packedFrameCount':32,'allPackedCellsRGBAEqual':True,'sheets':packed_sheet_records},ensure_ascii=False,indent=2)+'\n')
        run_output_logger.info('complete 32프레임·4×4 두 장·모든 셀 RGBA 보존')
    except Exception:
        run_output_logger.exception('failed 패킹 실패')
        print('\n'.join((packed_output_root/'execution.log').read_text().splitlines()[-20:]))
        raise
    finally:
        for output_log_handler in tuple(run_output_logger.handlers):
            run_output_logger.removeHandler(output_log_handler)
            output_log_handler.close()


if __name__ == '__main__':
    argument_value_parser = argparse.ArgumentParser(description=__doc__)
    argument_value_parser.add_argument('--normalized-dir', type=Path, required=True)
    argument_value_parser.add_argument('--output-dir', type=Path, required=True)
    parsed_argument_values = argument_value_parser.parse_args()
    pack_walk_frames(parsed_argument_values.normalized_dir, parsed_argument_values.output_dir)
