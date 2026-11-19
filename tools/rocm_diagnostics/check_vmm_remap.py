#!/usr/bin/env python3
"""ROCm HSA 가상 주소 재사용 시 이전·새 할당의 데이터 보존을 검사한다."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

PROBE_SOURCE_PATH = Path(__file__).with_name('hsa_vmm_remap_probe.cpp')


def read_gpu_compute_processes():
    result_values = subprocess.run(['amd-smi', 'process', '--json'], text=True, capture_output=True, timeout=10, check=True)
    device_record_values = json.loads(result_values.stdout)
    if not isinstance(device_record_values, list) or not device_record_values:
        raise ValueError('GPU 프로세스 목록이 비어 있거나 형식이 잘못됐습니다')
    process_identifier_values = set()
    for device_record_value in device_record_values:
        if not isinstance(device_record_value, dict) or not isinstance(device_record_value.get('process_list'), list):
            raise ValueError('GPU 프로세스 목록 형식이 잘못됐습니다')
        for process_record_value in device_record_value['process_list']:
            process_info_value = process_record_value.get('process_info')
            if isinstance(process_info_value, dict):
                process_identifier_values.add(int(process_info_value['pid']))
            elif process_info_value != 'No running processes detected':
                raise ValueError('알 수 없는 GPU 프로세스 정보')
    return process_identifier_values


def stop_probe_process_group(probe_process_handle):
    if probe_process_handle.poll() is not None:
        return
    try:
        os.killpg(probe_process_handle.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        probe_process_handle.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(probe_process_handle.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        probe_process_handle.wait()


def collect_process_group_members(probe_process_handle):
    process_table_result = subprocess.run(['ps', '-eo', 'pid=,pgid='], capture_output=True, text=True, timeout=5, check=True)
    return {int(pid_value) for pid_value, group_value in (line.split() for line in process_table_result.stdout.splitlines()) if int(group_value) == probe_process_handle.pid}


def execute_probe_case(binary_file_path, selected_address_mode, timeout_seconds_value):
    if read_gpu_compute_processes():
        raise RuntimeError('다른 GPU 연산이 실행 중입니다')
    probe_environment_values = os.environ.copy()
    # ROCm 선택을 바꾸지 않으며, 설정된 환경을 결과에 기록한다.
    probe_environment_values['TRACE_ADDRESS_MODE'] = selected_address_mode
    with tempfile.TemporaryFile(mode='w+t') as stdout_file_handle, tempfile.TemporaryFile(mode='w+t') as stderr_file_handle:
        probe_process_handle = subprocess.Popen([str(binary_file_path)], env=probe_environment_values, stdout=stdout_file_handle, stderr=stderr_file_handle, start_new_session=True)
        start_time_value = time.monotonic()
        try:
            while probe_process_handle.poll() is None:
                other_process_values = read_gpu_compute_processes() - collect_process_group_members(probe_process_handle)
                if other_process_values:
                    raise RuntimeError(f'다른 GPU 연산이 시작돼 진단을 중단합니다: {sorted(other_process_values)}')
                if time.monotonic() - start_time_value > timeout_seconds_value:
                    raise TimeoutError('진단 제한 시간이 초과됐습니다')
                time.sleep(0.25)
        finally:
            stop_probe_process_group(probe_process_handle)
        stdout_file_handle.seek(0)
        stderr_file_handle.seek(0)
        stdout_text_value, stderr_text_value = stdout_file_handle.read(), stderr_file_handle.read()
        if probe_process_handle.returncode:
            raise RuntimeError(f'HSA 진단 종료 코드 {probe_process_handle.returncode}: {stderr_text_value[-2000:]}')
    match_record_values = [re.fullmatch(r'(\d+) (\d+) (\d+) old=([0-9a-f]{2}) new=([0-9a-f]{2})', line) for line in stdout_text_value.splitlines()]
    if len(match_record_values) != 20 or any(value is None for value in match_record_values):
        raise ValueError('반복 결과가 20개가 아니거나 형식이 잘못됐습니다')
    rows_record_values = [{'iteration': int(value[1]), 'old_mismatch_bytes': int(value[2]), 'new_mismatch_bytes': int(value[3]), 'old_first_byte': value[4], 'new_first_byte': value[5]} for value in match_record_values]
    if [value['iteration'] for value in rows_record_values] != list(range(20)):
        raise ValueError('반복 번호가 불연속입니다')
    gpu_agent_match_value = re.search(r'^HSA_GPU_AGENT=(.+)$', stderr_text_value, re.MULTILINE)
    if not gpu_agent_match_value:
        raise ValueError('실제로 선택된 GPU 정보를 확인할 수 없습니다')
    return {'gpu_agent': gpu_agent_match_value.group(1), 'rows': rows_record_values, 'elapsed_seconds': round(time.monotonic() - start_time_value, 3), 'stderr': stderr_text_value}



def read_environment_metadata():
    """장치 식별에 필요한 버전만 수집하고 실패는 미측정으로 기록한다."""
    metadata_record_values = {}
    loaded_driver_path = Path('/sys/module/amdgpu/srcversion')
    try:
        metadata_record_values['loaded_amdgpu_srcversion'] = loaded_driver_path.read_text().strip()
    except OSError as metadata_error_value:
        metadata_record_values['loaded_amdgpu_srcversion'] = {'unavailable': str(metadata_error_value)}
    for metadata_name_value, command_argument_values in (
        ('amdgpu_srcversion', ['modinfo', '-F', 'srcversion', 'amdgpu']),
        ('amdgpu_version', ['modinfo', '-F', 'version', 'amdgpu']),
        ('amd_smi_version', ['amd-smi', 'version', '--json']),
    ):
        try:
            result_process_value = subprocess.run(command_argument_values, capture_output=True, text=True, check=True, timeout=10)
            metadata_record_values[metadata_name_value] = result_process_value.stdout.strip() or None
        except (OSError, subprocess.SubprocessError) as metadata_error_value:
            metadata_record_values[metadata_name_value] = {'unavailable': str(metadata_error_value)}
    return metadata_record_values

def main():
    argument_parser_value = argparse.ArgumentParser(description=__doc__)
    argument_parser_value.add_argument('--rocm-root', type=Path, default=Path('/opt/rocm'), help='HSA 헤더와 라이브러리가 있는 ROCm 경로')
    argument_parser_value.add_argument('--output', type=Path, required=True, help='새 결과 JSON 경로 (기존 파일 덮어쓰기 금지)')
    argument_parser_value.add_argument('--timeout', type=int, default=120, help='조건별 제한 시간(초)')
    argument_values = argument_parser_value.parse_args()
    if not 1 <= argument_values.timeout <= 1800:
        argument_parser_value.error('--timeout은 1~1800이어야 합니다')
    output_file_path = argument_values.output
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # O_EXCL은 기존 결과 및 심볼릭 링크를 보호한다.
        output_file_handle = output_file_path.open('x', encoding='utf-8')
    except FileExistsError:
        argument_parser_value.error('결과 파일이 이미 존재합니다')
    report_record_values = {'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'kernel': platform.release(), 'rocm_root': str(argument_values.rocm_root), 'probe_sha256': hashlib.sha256(PROBE_SOURCE_PATH.read_bytes()).hexdigest(), 'status': 'incomplete', 'cases': {}, 'environment': {key: value for key, value in os.environ.items() if key in ('HSA_ENABLE_SDMA', 'HSA_OVERRIDE_GFX_VERSION', 'HIP_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES', 'PYTORCH_ALLOC_CONF')}}
    try:
        if not shutil.which('amd-smi') or not shutil.which('g++'):
            raise RuntimeError('amd-smi와 g++가 필요합니다')
        if read_gpu_compute_processes():
            raise RuntimeError('다른 GPU 연산이 실행 중입니다')
        report_record_values['versions'] = read_environment_metadata()
        rocm_directory_path = argument_values.rocm_root.resolve()
        with tempfile.TemporaryDirectory(prefix='rocm-vmm-probe-') as temporary_directory_value:
            binary_file_path = Path(temporary_directory_value) / 'hsa_vmm_probe'
            command_argument_values = ['g++', '-std=c++17', '-O2', f'-I{rocm_directory_path / "include"}', str(PROBE_SOURCE_PATH), f'-L{rocm_directory_path / "lib"}', f'-Wl,-rpath,{rocm_directory_path / "lib"}', '-lhsa-runtime64', '-o', str(binary_file_path)]
            subprocess.run(command_argument_values, check=True, capture_output=True, text=True, timeout=120)
            for selected_address_mode in ('same', 'different'):
                print(f'{selected_address_mode}: 20회 검사 중', flush=True)
                report_record_values['cases'][selected_address_mode] = execute_probe_case(binary_file_path, selected_address_mode, argument_values.timeout)
        report_record_values['status'] = 'fail' if any(row['old_mismatch_bytes'] or row['new_mismatch_bytes'] for case in report_record_values['cases'].values() for row in case['rows']) else 'pass'
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error_value:
        report_record_values['error'] = str(error_value)
        if isinstance(error_value, subprocess.CalledProcessError) and error_value.stderr:
            report_record_values['error_detail'] = error_value.stderr[-3000:]
    finally:
        report_record_values['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        json.dump(report_record_values, output_file_handle, ensure_ascii=False, indent=2)
        output_file_handle.write('\n')
        output_file_handle.close()
    print(f"결과: {report_record_values['status']} · {output_file_path}", flush=True)
    return {'pass': 0, 'fail': 1, 'incomplete': 2}[report_record_values['status']]


if __name__ == '__main__':
    sys.exit(main())
