"""독립 실행 가능한 관리도구 브라우저 계약을 공용 회귀 실행기에 연결한다."""
from pathlib import Path
import subprocess
import unittest

MANAGEMENT_BROWSER_TEST_SCRIPTS = (
    'frame_player_loop.test.mjs',
    'animation_anchor_native.test.mjs',
    'sprite_sheet_slicer.test.mjs',
    'frame_manager_ui.test.mjs',
    'animation_action_review.test.mjs',
)


class ManagementBrowserScriptTests(unittest.TestCase):
    def test_standalone_browser_script_contracts(self):
        for current_script_name in MANAGEMENT_BROWSER_TEST_SCRIPTS:
            with self.subTest(script=current_script_name):
                current_script_path = Path(__file__).with_name(current_script_name)
                current_process_result = subprocess.run(
                    ['node', str(current_script_path)], capture_output=True,
                    text=True, timeout=30,
                )
                self.assertEqual(
                    current_process_result.returncode, 0,
                    current_script_name + '\n' + current_process_result.stdout + current_process_result.stderr,
                )

    def test_generated_anchor_editor_contract(self):
        import json
        import tempfile
        from tools.review.ui_assets import read_animation_anchor_template
        current_direction_names = ('down_left', 'down_right', 'up_left', 'up_right')
        current_frame_records = [
            {'frameId': f'{current_direction_name}.{current_frame_index}', 'direction': current_direction_name,
             'image': current_direction_name + '.png', 'rect': {'x': current_frame_index * 100, 'y': 0, 'width': 100, 'height': 100},
             'anchor': {'x': 50, 'y': 90}, 'contacts': [{'x': 50, 'y': 90}], 'endpoints': []}
            for current_direction_name in current_direction_names for current_frame_index in range(8)
        ]
        current_source_metadata = {
            'animationId': 'isolated-walk', 'animationVersion': 'v1', 'coordinateMode': 'anchor',
            'description': '격리 검증용 합성 프레임', 'artifactType': 'character-animation-anchor-review',
            'sheets': [{'image': current_direction_name + '.png', 'sha256': '0' * 64} for current_direction_name in current_direction_names],
            'gameRenderMetrics': {'tileWidth': 64, 'tileHeight': 32, 'characterHeight': 60},
            'runtimeScale': {'baseHeight': 60, 'sourceHeight': 100},
        }
        current_page_source = read_animation_anchor_template().replace('__FRAME_RECORDS__', json.dumps(current_frame_records)).replace('__SOURCE_METADATA__', json.dumps(current_source_metadata))
        with tempfile.TemporaryDirectory() as current_directory_name:
            current_page_path = Path(current_directory_name) / 'anchors.html'
            current_page_path.write_text(current_page_source)
            current_process_result = subprocess.run(
                ['node', str(Path(__file__).with_name('animation_anchor_ui.test.mjs')), str(current_page_path)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(current_process_result.returncode, 0, current_process_result.stdout + current_process_result.stderr)
