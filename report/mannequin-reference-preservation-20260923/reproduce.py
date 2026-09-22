"""보관 사본만으로 리그를 재생성하고 수치 동등성을 확인한다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
import traceback

ARCHIVE_SOURCE_ROOT = Path(__file__).resolve().parent
NUMERIC_ERROR_LIMIT = 1e-6
NORMAL_COMPONENT_LIMIT = 1e-4
EXECUTION_TRACE_PATH = None


def write_trace_message(stage_name_value, message_text_value):
    trace_message_value = f'{datetime.now().astimezone().isoformat()}/mannequin-reproduction/{stage_name_value} {message_text_value}'
    print(trace_message_value, flush=True)
    if EXECUTION_TRACE_PATH is not None:
        with EXECUTION_TRACE_PATH.open('a') as execution_log_stream:
            execution_log_stream.write(trace_message_value + '\n')


def verify_archive_integrity():
    checksum_file_path = ARCHIVE_SOURCE_ROOT / 'checksums.sha256'
    expected_file_names = set()
    for checksum_line_value in checksum_file_path.read_text().splitlines():
        expected_digest_value, relative_file_name = checksum_line_value.split('  ', 1)
        candidate_file_path = (ARCHIVE_SOURCE_ROOT / relative_file_name).resolve()
        if not candidate_file_path.is_relative_to(ARCHIVE_SOURCE_ROOT):
            raise ValueError('사본 범위를 벗어난 해시 경로')
        if hashlib.sha256(candidate_file_path.read_bytes()).hexdigest() != expected_digest_value:
            raise ValueError(f'사본 해시 불일치: {relative_file_name}')
        expected_file_names.add(relative_file_name)
    actual_file_names = {str(candidate_file_path.relative_to(ARCHIVE_SOURCE_ROOT)) for candidate_file_path in ARCHIVE_SOURCE_ROOT.rglob('*') if candidate_file_path.is_file() and '__pycache__' not in candidate_file_path.parts and candidate_file_path != checksum_file_path}
    if actual_file_names != expected_file_names:
        raise ValueError(f'사본 목록 불일치: {actual_file_names ^ expected_file_names}')
    write_trace_message('integrity', f'{len(expected_file_names)}개 파일 SHA-256 일치')
    return len(expected_file_names)


def replace_exact_text(source_text_value, original_text_value, replacement_text_value):
    if source_text_value.count(original_text_value) != 1:
        raise ValueError(f'재현 코드 어댑터 대상 불일치: {original_text_value}')
    return source_text_value.replace(original_text_value, replacement_text_value)


def run_logged_stage(stage_name_value, command_argument_values, execution_output_root):
    stage_log_path = execution_output_root / f'{stage_name_value}.log'
    write_trace_message(stage_name_value, repr(command_argument_values))
    with stage_log_path.open('w') as stage_log_stream:
        child_process_value = subprocess.Popen(command_argument_values, cwd=execution_output_root, stdout=stage_log_stream, stderr=subprocess.STDOUT)
        while True:
            try:
                process_exit_value = child_process_value.wait(timeout=5)
                break
            except subprocess.TimeoutExpired:
                recent_log_lines = stage_log_path.read_text(errors='replace').splitlines()
                write_trace_message('heartbeat', f'{stage_name_value}: lines={len(recent_log_lines)} bytes={stage_log_path.stat().st_size} recent={recent_log_lines[-1:]}')
    if process_exit_value != 0:
        print('\n'.join(stage_log_path.read_text(errors='replace').splitlines()[-35:]))
        raise RuntimeError(f'{stage_name_value} 종료 코드 {process_exit_value}, command={command_argument_values}')


def read_glb_accessors(binary_file_path):
    import numpy as np
    import struct
    binary_file_bytes = binary_file_path.read_bytes()
    json_chunk_length = struct.unpack_from('<I', binary_file_bytes, 12)[0]
    gltf_source_record = json.loads(binary_file_bytes[20:20 + json_chunk_length])
    binary_payload_bytes = binary_file_bytes[28 + json_chunk_length:]
    component_type_values = {5126:'<f4', 5123:'<u2', 5125:'<u4', 5121:'u1'}
    component_width_values = {'SCALAR':1, 'VEC2':2, 'VEC3':3, 'VEC4':4, 'MAT4':16}
    accessor_array_values = []
    for accessor_source_record in gltf_source_record['accessors']:
        buffer_source_record = gltf_source_record['bufferViews'][accessor_source_record['bufferView']]
        component_dtype_value = np.dtype(component_type_values[accessor_source_record['componentType']])
        component_width_value = component_width_values[accessor_source_record['type']]
        component_offset_value = buffer_source_record.get('byteOffset', 0) + accessor_source_record.get('byteOffset', 0)
        component_stride_value = buffer_source_record.get('byteStride', component_dtype_value.itemsize * component_width_value)
        accessor_array_values.append(np.ndarray((accessor_source_record['count'], component_width_value), dtype=component_dtype_value, buffer=binary_payload_bytes, offset=component_offset_value, strides=(component_stride_value, component_dtype_value.itemsize)).copy())
    return gltf_source_record, accessor_array_values


def execute_reproduction_run():
    global EXECUTION_TRACE_PATH
    import numpy as np
    import importlib.metadata
    argument_parser_value = argparse.ArgumentParser(description=__doc__)
    argument_parser_value.add_argument('--verify-only', action='store_true')
    argument_parser_value.add_argument('--output', type=Path)
    parsed_argument_values = argument_parser_value.parse_args()
    verified_file_count = verify_archive_integrity()
    if parsed_argument_values.verify_only:
        return
    if parsed_argument_values.output is None:
        raise ValueError('원본 보호를 위해 --output 새 실행 폴더를 지정해야 합니다.')
    execution_output_root = parsed_argument_values.output.resolve()
    if execution_output_root.is_relative_to(ARCHIVE_SOURCE_ROOT):
        raise ValueError('재현 출력은 보관 사본 밖의 새 폴더여야 합니다.')
    execution_output_root.mkdir(parents=True, exist_ok=False)
    EXECUTION_TRACE_PATH = execution_output_root / 'execution.log'
    write_trace_message('start', f'archive={ARCHIVE_SOURCE_ROOT} output={execution_output_root} inputs=accepted-mannequin.blend,mannequin-motion.npz verified_files={verified_file_count}')
    execution_result_record = {'status':'running', 'started_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(), 'archive_files_verified':verified_file_count, 'python':sys.version, 'blender':importlib.metadata.version('bpy'), 'numpy':np.__version__, 'scope':'accepted mesh -> surface partitions -> weights -> rig -> GLB -> 25-frame validation; no inference or rendering'}
    try:
        shutil.copytree(ARCHIVE_SOURCE_ROOT / 'inputs', execution_output_root / 'inputs')
        for source_file_name in ['build_rig.py','build_parts.py','refine_weights.py','validate_rig.py','validate_export.py']:
            shutil.copy2(ARCHIVE_SOURCE_ROOT / 'source' / source_file_name, execution_output_root / source_file_name)
        rig_script_path = execution_output_root / 'build_rig.py'
        rig_script_text = rig_script_path.read_text()
        rig_script_text = replace_exact_text(rig_script_text, "SOURCE_BLEND_PATH=Path('/home/cbsim/ws/slime-workflow/.tmp/2026-09-23_01-02-22/model-review/mannequin.blend')", "SOURCE_BLEND_PATH=EXPERIMENT_OUTPUT_ROOT/'inputs/accepted-mannequin.blend'")
        rig_script_text = replace_exact_text(rig_script_text, "SOURCE_MOTION_PATH=WORKFLOW_SOURCE_ROOT/'assets/motion-sheet/mannequin-walk-v1/mannequin-motion.npz'", "SOURCE_MOTION_PATH=EXPERIMENT_OUTPUT_ROOT/'inputs/mannequin-motion.npz'")
        render_start_index = rig_script_text.index(' device_preferences_value=')
        render_finish_index = rig_script_text.index(' result_record_value=', render_start_index)
        rig_script_text = rig_script_text[:render_start_index] + " write_trace_message('render-skipped','사본 재현은 형상·리그·GLB 수치 검증이며 렌더는 별도 보관본 참조')\n" + rig_script_text[render_finish_index:]
        rig_script_path.write_text(rig_script_text)
        parts_script_path = execution_output_root / 'build_parts.py'
        parts_script_path.write_text(replace_exact_text(parts_script_path.read_text(), "SOURCE_MODEL_FILE='/home/cbsim/ws/slime-workflow/.tmp/2026-09-23_01-02-22/model-review/mannequin.blend'", "from pathlib import Path\nSOURCE_MODEL_FILE=str(Path(__file__).resolve().parent/'inputs/accepted-mannequin.blend')"))
        # bpy 4.5.3의 인터프리터 종료 정체를 피하되 모든 예외는 종료 코드 1로 전파한다.
        execution_wrapper_text = "import os,runpy,sys,traceback\nprocess_exit_value=0\ntry:\n sys.path.insert(0,os.path.dirname(sys.argv[1]))\n runpy.run_path(sys.argv[1],run_name='__main__')\nexcept BaseException:\n traceback.print_exc()\n process_exit_value=1\nfinally:\n sys.stdout.flush()\n sys.stderr.flush()\n os._exit(process_exit_value)\n"
        for stage_script_name in ['build_rig.py','validate_rig.py','validate_export.py']:
            run_logged_stage(Path(stage_script_name).stem, [sys.executable, '-c', execution_wrapper_text, str(execution_output_root / stage_script_name)], execution_output_root)
        for validation_file_name in ['validation.json','export-validation.json']:
            if json.loads((execution_output_root / validation_file_name).read_text())['status'] != 'passed':
                raise ValueError(f'검증 실패: {validation_file_name}')
        expected_gltf_record, expected_accessor_arrays = read_glb_accessors(ARCHIVE_SOURCE_ROOT / 'snapshot/rigged-mannequin.glb')
        reproduced_gltf_record, reproduced_accessor_arrays = read_glb_accessors(execution_output_root / 'rigged-mannequin.glb')
        if expected_gltf_record != reproduced_gltf_record:
            raise ValueError('GLB JSON 구조 또는 메타데이터 불일치')
        if len(expected_accessor_arrays) != len(reproduced_accessor_arrays):
            raise ValueError('GLB accessor 개수 불일치')
        triangle_accessor_indices = {primitive_record_value['indices'] for mesh_record_value in expected_gltf_record['meshes'] for primitive_record_value in mesh_record_value['primitives']}
        normal_accessor_indices = {primitive_record_value['attributes']['NORMAL'] for mesh_record_value in expected_gltf_record['meshes'] for primitive_record_value in mesh_record_value['primitives']}
        maximum_accessor_error = 0.0
        maximum_normal_error = 0.0
        reordered_triangle_accessors = 0
        for accessor_index_value, (expected_array_value, reproduced_array_value) in enumerate(zip(expected_accessor_arrays, reproduced_accessor_arrays, strict=True)):
            if expected_array_value.shape != reproduced_array_value.shape or expected_array_value.dtype != reproduced_array_value.dtype:
                raise ValueError('GLB accessor 형상/자료형 불일치')
            if accessor_index_value in triangle_accessor_indices:
                def canonical_triangle_list(triangle_index_values):
                    return sorted(min(tuple(triangle_value), tuple(np.roll(triangle_value, 1)), tuple(np.roll(triangle_value, 2))) for triangle_value in triangle_index_values.reshape(-1, 3))
                if canonical_triangle_list(expected_array_value) != canonical_triangle_list(reproduced_array_value):
                    raise ValueError('삼각형 연결 또는 winding 불일치')
                reordered_triangle_accessors += int(not np.array_equal(expected_array_value, reproduced_array_value))
                continue
            current_accessor_error = float(np.max(np.abs(expected_array_value.astype(float)-reproduced_array_value.astype(float))))
            accessor_error_limit = NORMAL_COMPONENT_LIMIT if accessor_index_value in normal_accessor_indices else NUMERIC_ERROR_LIMIT
            if accessor_index_value in normal_accessor_indices:
                maximum_normal_error = max(maximum_normal_error, current_accessor_error)
            else:
                maximum_accessor_error = max(maximum_accessor_error, current_accessor_error)
            if not np.allclose(expected_array_value, reproduced_array_value, atol=accessor_error_limit, rtol=0):
                raise ValueError('GLB 좌표/가중치/인덱스/애니메이션 수치 불일치')
        maximum_motion_error = 0.0
        for motion_file_name in ['retargeted-motion.npz','verified-baked-motion.npz']:
            with np.load(ARCHIVE_SOURCE_ROOT/'snapshot'/motion_file_name, allow_pickle=False) as expected_motion_bundle, np.load(execution_output_root/motion_file_name, allow_pickle=False) as reproduced_motion_bundle:
                if set(expected_motion_bundle.files) != set(reproduced_motion_bundle.files):
                    raise ValueError('모션 NPZ 필드 불일치')
                for motion_field_name in expected_motion_bundle.files:
                    expected_field_array = expected_motion_bundle[motion_field_name]
                    reproduced_field_array = reproduced_motion_bundle[motion_field_name]
                    if expected_field_array.shape != reproduced_field_array.shape or not np.allclose(expected_field_array, reproduced_field_array, atol=NUMERIC_ERROR_LIMIT, rtol=0):
                        raise ValueError(f'모션 수치 불일치: {motion_file_name}/{motion_field_name}')
                    maximum_motion_error = max(maximum_motion_error, float(np.max(np.abs(expected_field_array-reproduced_field_array))))
        execution_result_record.update(status='passed', max_accessor_error=maximum_accessor_error, max_motion_error=maximum_motion_error, max_normal_component_error=maximum_normal_error, normal_tolerance=NORMAL_COMPONENT_LIMIT, reordered_triangle_accessors=reordered_triangle_accessors, triangle_connectivity_and_winding_equal=True, tolerance=NUMERIC_ERROR_LIMIT, accessors_compared=len(expected_accessor_arrays), glb_sha256=hashlib.sha256((execution_output_root/'rigged-mannequin.glb').read_bytes()).hexdigest(), source_glb_sha256=hashlib.sha256((ARCHIVE_SOURCE_ROOT/'snapshot/rigged-mannequin.glb').read_bytes()).hexdigest())
        write_trace_message('complete', str(execution_result_record))
    except Exception:
        execution_result_record.update(status='failed', error=traceback.format_exc())
        write_trace_message('failure', execution_result_record['error'])
        raise
    finally:
        (execution_output_root/'reproduction-result.json').write_text(json.dumps(execution_result_record, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    execute_reproduction_run()
