"""관리도구 공용 계약과 활성 페이지를 기존 회귀 실행기로 검사한다."""
from pathlib import Path
import argparse
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.tests.run_music_regression import execute_music_regression

MANAGEMENT_AUDIT_MODULES = tuple('tools.review.tests.' + current_module_name for current_module_name in (
    'test_reference_video_resume_validation', 'test_dwpose_generation', 'test_video_job_recovery', 'test_kimodo_generation', 'test_kimodo_dwpose', 'test_kimodo_migraphx_build', 'test_kimodo_readiness', 'test_hymotion_retirement',
    'test_content_launch_config', 'test_gateway_existing_process', 'test_gateway_trace', 'test_gateway_watch',
    'test_review_startup', 'test_review_startup_menu', 'test_review_watch', 'test_management_menu_offline', 'test_gradio_error_trace',
    'test_regression_runner', 'test_management_browser_scripts', 'test_landmarks_retirement', 'test_host_memory_guard',
    'test_gpu_confirmation', 'test_gradio_button_guidance', 'test_browser_gpu_confirmation', 'test_gradio_history', 'test_gradio_history_inputs', 'test_history_thumbnail_loading',
    'test_gradio_proxy_response', 'test_gradio_standard_components', 'test_generation_status_display', 'test_generation_status_lookup', 'test_generation_estimates',
    'test_generation_cleanup', 'test_queue_generation_telemetry', 'test_generation_history', 'test_gpu_queue_priority',
    'test_gpu_job_queue', 'test_kimodo_cache_queue_integration', 'test_gpu_memory_history', 'test_gpu_status', 'test_anny_retirement',
    'test_anchor_history', 'test_anchor_asset_update', 'test_history_preservation', 'test_gradio_process', 'test_management_single_port', 'test_management_heartbeat_bridge', 'test_review_server_takeover',
    'test_generation_records_observe', 'test_management_gateway', 'test_management_runtime', 'test_management_launcher', 'test_management_menu_gradio', 'test_model_management', 'test_hermes_model_download', 'test_hermes_workspace_snapshot', 'test_hermes_service', 'test_hermes_gateway_restart', 'test_hermes_delegation', 'test_hermes_capture_delegation', 'test_hermes_capture_worker', 'test_hermes_capture_queue', 'test_hermes_capture_status', 'test_hermes_capture_command', 'test_hermes_billboard_operations', 'test_hermes_building_operations', 'test_hermes_keyframe_observer', 'test_hermes_effect_observer', 'test_hermes_sprite_observer', 'test_hermes_sprite_operations', 'test_hermes_effect_operations', 'test_hermes_video_operations', 'test_hermes_audio_operations', 'test_hermes_failure_observer', 'test_hermes_flux_profile_operations', 'test_hermes_writer_operations', 'test_writer_cancel_queue_integration', 'test_hermes_translation_operations', 'test_hermes_city_map_operations', 'test_hermes_field_map_operations', 'test_hermes_model_preparation_store', 'test_hermes_process_cleanup', 'test_hermes_gradio', 'test_hermes_predict_diagnostic', 'test_hermes_mcp', 'test_hermes_mcp_transport_registry', 'test_hermes_worker', 'test_image_generation', 'test_prompt_translation',
    'test_hermes_map_source_observer', 'test_billboard_building_unification', 'test_content_ledger_publication', 'test_content_ledger_sync', 'test_asset_ledger_roundtrip', 'test_pose_transfer_retirement', 'test_anypose_retirement',
    'test_mannequin_generator', 'test_character_generator', 'test_character_body_references', 'test_generator_changelog', 'test_three_reference_generation', 'test_qwen_21_generation', 'test_qwen_archive_policy', 'test_flux_expression_generation', 'test_flux_image_generation', 'test_flux_model_prepare', 'test_expression_lora_preparation', 'test_qwen_2511_progress','test_qwen_circular_generation', 'test_expression_generation',
    'test_animation_separation_retirement', 'test_sprite_sheet_editor', 'test_management_separation',
    'test_retired_management_ui', 'test_qwen_commands', 'test_qwen_2511_gradio', 'test_qwen_2511_retirement',
    'test_effect_editor', 'test_asset_service_http', 'test_building_editor', 'test_building_lifecycle', 'test_database_asset_editor', 'test_database_seed_command', 'test_map_asset_resize', 'test_map_asset_editor', 'test_map_asset_anchors', 'test_city_layout_editor', 'test_map_layout_editor', 'test_map_asset_sources', 'test_map_wall_materials', 'test_map_source_alignment_review', 'test_map_brushes', 'test_map_review_gradio', 'test_map_review_lifecycle', 'test_map_review_capture', 'test_character_review_capture', 'test_review_asset_publication',
    'test_static_review_gradio',
    'test_floor_generation', 'test_seamless_pattern', 'test_seamless_generation',
    'test_dasheng_audio_sfx', 'test_music_generation', 'test_music_management_audit', 'test_magenta_generation', 'test_rocm_audio_guards', 'test_heartmula_separation', 'test_wan_animate2_generation', 'test_wan_animate_retirement', 'test_wan_fun_generation', 'test_wan_fun_model_prepare', 'test_wan_vace_generation', 'test_vace_video_edit', 'test_vace_official_runtime', 'test_wan_vace_sampling', 'test_writer_agent_gradio',
)) + ('generators.animation.tests.test_qwen_pose', 'generators.writer_agent.tests.test_writer_agent', 'generators.writer_agent.tests.test_writer_api')

MANAGEMENT_AUDIT_GROUPS = {
    'hermes': tuple(current_module_name for current_module_name in MANAGEMENT_AUDIT_MODULES if '.test_hermes_' in current_module_name),
    'gpu': tuple(current_module_name for current_module_name in MANAGEMENT_AUDIT_MODULES if current_module_name.rsplit('.', 1)[-1] in ('test_gpu_job_queue', 'test_gpu_memory_history', 'test_gpu_status', 'test_gpu_queue_priority', 'test_gpu_confirmation')),
    'management': tuple(current_module_name for current_module_name in MANAGEMENT_AUDIT_MODULES if current_module_name.rsplit('.', 1)[-1] in ('test_management_gateway', 'test_management_runtime', 'test_management_launcher', 'test_management_menu_gradio', 'test_management_single_port', 'test_content_launch_config', 'test_gateway_existing_process', 'test_gateway_trace', 'test_gateway_watch', 'test_review_startup', 'test_review_watch', 'test_management_menu_offline', 'test_gradio_error_trace', 'test_regression_runner')),
}


def run_management_audit_cli(audit_argument_values=None):
    current_argument_parser = argparse.ArgumentParser(description=__doc__)
    current_scope_group = current_argument_parser.add_mutually_exclusive_group(required=True)
    current_scope_group.add_argument('--module', action='append', metavar='MODULE', help='등록된 테스트 모듈. 여러 모듈은 반복 지정하며 --list-all로 확인합니다.')
    current_scope_group.add_argument('--group', choices=tuple(MANAGEMENT_AUDIT_GROUPS), help='등록된 영역 검사')
    current_scope_group.add_argument('--list-group', choices=tuple(MANAGEMENT_AUDIT_GROUPS), help='실행 없이 영역에 포함된 모듈 표시')
    current_scope_group.add_argument('--list-all', action='store_true', help='실행 없이 등록된 전체 관리 회귀 모듈 표시')
    current_scope_group.add_argument('--all', action='store_true', help='등록된 전체 관리 회귀 모듈 실행 (저장소의 모든 테스트 파일은 아님)')
    current_argument_values = current_argument_parser.parse_args(audit_argument_values)
    if current_argument_values.module:
        for current_module_name in current_argument_values.module:
            if current_module_name not in MANAGEMENT_AUDIT_MODULES:
                current_argument_parser.error(f'등록되지 않은 모듈: {current_module_name}. --list-all로 확인하세요.')
    if current_argument_values.list_all:
        print('\n'.join(MANAGEMENT_AUDIT_MODULES))
        return 0
    if current_argument_values.list_group:
        print('\n'.join(MANAGEMENT_AUDIT_GROUPS[current_argument_values.list_group]))
        return 0
    current_selected_modules = (MANAGEMENT_AUDIT_MODULES if current_argument_values.all else
        MANAGEMENT_AUDIT_GROUPS[current_argument_values.group] if current_argument_values.group else tuple(dict.fromkeys(current_argument_values.module)))
    return execute_music_regression(current_selected_modules, 'management-audit')


if __name__ == '__main__':
    raise SystemExit(run_management_audit_cli())
