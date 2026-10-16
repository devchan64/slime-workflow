"""관리도구 공용 계약과 활성 페이지를 기존 회귀 실행기로 검사한다."""
from pathlib import Path
import argparse
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.tests.run_music_regression import execute_music_regression

MANAGEMENT_AUDIT_MODULES = tuple('tools.review.tests.' + current_module_name for current_module_name in (
    'test_regression_runner', 'test_management_browser_scripts', 'test_anny_landmarks',
    'test_gpu_confirmation', 'test_gradio_button_guidance', 'test_browser_gpu_confirmation', 'test_gradio_history', 'test_gradio_history_inputs',
    'test_gradio_proxy_response', 'test_gradio_standard_components', 'test_generation_status_display', 'test_generation_status_lookup', 'test_hy_motion_progress_display', 'test_generation_estimates',
    'test_generation_cleanup', 'test_queue_generation_telemetry', 'test_generation_history', 'test_gpu_queue_priority',
    'test_gpu_job_queue', 'test_gpu_memory_history', 'test_gpu_status', 'test_anny_history', 'test_anny_profiles',
    'test_anchor_history', 'test_history_preservation', 'test_gradio_process',
    'test_management_gateway', 'test_management_runtime', 'test_management_menu_gradio',
    'test_hy_motion', 'test_pose_transfer_generation', 'test_pose_reference_manifest',
    'test_three_reference_generation', 'test_qwen_21_generation', 'test_qwen_2511_progress','test_qwen_2512_progress', 'test_qwen_circular_generation', 'test_outfit_transfer', 'test_expression_generation',
    'test_animation_separation', 'test_sprite_editor_v2', 'test_management_separation',
    'test_retired_management_ui', 'test_qwen_commands', 'test_qwen_2511_gradio',
    'test_qwen_2512_gradio', 'test_separation_preview_gradio', 'test_map_review_gradio', 'test_map_review_lifecycle', 'test_character_review_capture', 'test_review_asset_publication',
    'test_static_review_gradio', 'test_anny_attributes_gradio', 'test_sprite_editor_v2_gradio', 'test_sprite_browser_confirmation',
    'test_hy_motion_reload', 'test_floor_generation', 'test_seamless_pattern',
    'test_music_generation', 'test_music_management_audit', 'test_vace_generation', 'test_vace_timeline', 'test_vace_timeline_editor', 'test_phantom_generation', 'test_writer_agent_gradio', 'test_landmark_confirmation_gradio',
)) + ('generators.animation.tests.test_qwen_pose', 'generators.writer_agent.tests.test_writer_agent')

if __name__ == '__main__':
    current_argument_parser = argparse.ArgumentParser(description=__doc__)
    current_scope_group = current_argument_parser.add_mutually_exclusive_group(required=True)
    current_scope_group.add_argument('--module', action='append', choices=MANAGEMENT_AUDIT_MODULES, help='영향받는 테스트 모듈. 여러 모듈은 반복 지정합니다.')
    current_scope_group.add_argument('--all', action='store_true', help='전체 관리도구 회귀를 명시적으로 실행합니다.')
    current_argument_values = current_argument_parser.parse_args()
    current_selected_modules = MANAGEMENT_AUDIT_MODULES if current_argument_values.all else tuple(dict.fromkeys(current_argument_values.module))
    raise SystemExit(execute_music_regression(current_selected_modules, 'management-audit'))
