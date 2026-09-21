"""GPU 없이 타일 티켓과 참조 검증 계약을 확인한다."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from generators.terrain.qwen_tile.map_preview import validate_map_preview_snapshot
from generators.terrain.qwen_tile.runtime import validate_style_reference, validate_tile_set_ticket


def build_ticket_values(reference_sha256_value):
    """유효한 최소 타일 세트 티켓을 만든다."""
    return {'asset_id': 'field.grass-set-v1', 'tile_size': [128, 128], 'generation_size': [384, 384], 'tileability': 'repeat-both', 'tile_variants': ['ground', 'wall-front', 'wall-side'], 'style_reference_id': 'field-style-v1', 'style_reference_sha256': reference_sha256_value, 'prompt': 'Soft grassy soil with small stones.', 'height_steps': 2, 'acceptance': {'seam_check': True, 'transparent_background': False}}


class QwenTileTicketTest(unittest.TestCase):
    """타일 생성의 고정 모델·입력 계약을 시험한다."""

    def test_accepts_valid_ticket_and_reference(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            reference_path = Path(temporary_directory) / 'style.png'
            Image.new('RGB', (384, 384), (32, 96, 48)).save(reference_path)
            reference_sha256_value = hashlib.sha256(reference_path.read_bytes()).hexdigest()
            ticket_values = validate_tile_set_ticket(build_ticket_values(reference_sha256_value))
            prepared_image, actual_sha256_value = validate_style_reference(reference_path, reference_sha256_value, ticket_values['generation_size'])
            self.assertEqual(prepared_image.size, (384, 384))
            self.assertEqual(actual_sha256_value, reference_sha256_value)

    def test_rejects_model_selection_in_ticket(self):
        ticket_values = build_ticket_values('0' * 64)
        ticket_values['model'] = 'another-model'
        with self.assertRaises(ValueError):
            validate_tile_set_ticket(ticket_values)

    def test_rejects_invalid_experiment_size(self):
        ticket_values = build_ticket_values('0' * 64)
        ticket_values['generation_size'] = [274, 384]
        with self.assertRaises(ValueError):
            validate_tile_set_ticket(ticket_values)

    def test_rejects_unsupported_transparent_tile(self):
        ticket_values = build_ticket_values('0' * 64)
        ticket_values['acceptance']['transparent_background'] = True
        with self.assertRaises(ValueError):
            validate_tile_set_ticket(ticket_values)

    def test_rejects_partial_shape_reference_record(self):
        ticket_values = build_ticket_values('0' * 64)
        ticket_values['shape_reference_id'] = 'wall-shape-v1'
        with self.assertRaises(ValueError):
            validate_tile_set_ticket(ticket_values)

    def test_accepts_map_preview_with_target_cells(self):
        map_preview_value = {'schemaVersion': 1, 'mapId': 'meadow', 'displayNameKo': '이슬 초원', 'columns': 2, 'rows': 2,
                             'terrainRows': ['gg', 'gr'], 'terrainCodes': {'g': {'labelKo': '풀밭', 'color': '#39754a'}, 'r': {'labelKo': '흙길', 'color': '#90714a'}},
                             'targetCells': [{'column': 1, 'row': 1}]}
        self.assertEqual(validate_map_preview_snapshot(map_preview_value)['mapId'], 'meadow')

    def test_rejects_map_preview_outside_target_cell(self):
        map_preview_value = {'schemaVersion': 1, 'mapId': 'meadow', 'displayNameKo': '이슬 초원', 'columns': 1, 'rows': 1,
                             'terrainRows': ['g'], 'terrainCodes': {'g': {'labelKo': '풀밭', 'color': '#39754a'}},
                             'targetCells': [{'column': 1, 'row': 0}]}
        with self.assertRaises(ValueError):
            validate_map_preview_snapshot(map_preview_value)
