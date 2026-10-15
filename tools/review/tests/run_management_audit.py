"""관리도구 공용 계약과 활성 페이지를 기존 회귀 실행기로 검사한다."""
from tools.review.tests.run_music_regression import execute_music_regression

MANAGEMENT_AUDIT_MODULES = tuple('tools.review.tests.' + current_module_name for current_module_name in (
    'test_gpu_confirmation', 'test_browser_gpu_confirmation', 'test_gradio_history', 'test_gradio_history_inputs',
    'test_gradio_standard_components', 'test_generation_status_display', 'test_generation_estimates',
    'test_generation_cleanup', 'test_queue_generation_telemetry', 'test_generation_history', 'test_gpu_queue_priority',
    'test_management_gateway', 'test_management_runtime', 'test_management_menu_gradio',
    'test_retired_management_ui', 'test_qwen_commands', 'test_qwen_2511_gradio',
    'test_qwen_2512_gradio', 'test_separation_preview_gradio', 'test_map_review_gradio',
    'test_static_review_gradio', 'test_anny_attributes_gradio', 'test_sprite_editor_v2_gradio',
    'test_music_generation', 'test_vace_generation', 'test_phantom_generation', 'test_writer_agent_gradio',
))

if __name__ == '__main__':
    raise SystemExit(execute_music_regression(MANAGEMENT_AUDIT_MODULES, 'management-audit'))
