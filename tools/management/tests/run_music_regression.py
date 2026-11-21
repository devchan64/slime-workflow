"""음악 관련 회귀 검사를 로그·JUnit·종료 코드와 함께 한 번 실행한다."""
from datetime import datetime
import json
from pathlib import Path
import sys
import signal
import subprocess
import tempfile
import threading
import time
import unittest
import xml.etree.ElementTree as ElementTree
from zoneinfo import ZoneInfo

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
MUSIC_REGRESSION_MODULES = (
    'tools.management.tests.test_music_generation',
    'tools.management.tests.test_music_runtime_loading',
    'tools.management.tests.test_music_management_audit',
    'tools.management.tests.test_generation_cleanup',
    'tools.management.tests.test_gradio_history',
    'tools.management.tests.test_generation_estimates',
    'tools.management.tests.test_gpu_queue_priority',
    'tools.management.tests.test_management_gateway',
    'tools.management.tests.test_management_runtime',
    'tools.management.tests.test_management_menu_gradio',
    'tools.management.tests.test_hy_motion',
    'tools.management.tests.test_qwen_commands',
)


class MusicRegressionResult(unittest.TextTestResult):
    """비동기 테스트가 멈춰도 원인·실패를 저장하고 종료한다."""
    def startTest(self,current_test_case):
        super().startTest(current_test_case)
        current_test_method=getattr(current_test_case,current_test_case._testMethodName)
        current_timeout_seconds=getattr(current_test_method,'regression_timeout_seconds',30)
        if type(current_timeout_seconds) is not int or not 1<=current_timeout_seconds<=600:
            raise ValueError('회귀 검사 제한 시간은 1~600초 정수여야 합니다.')
        self.current_timeout_seconds=current_timeout_seconds
        signal.signal(signal.SIGALRM,self.raise_test_timeout)
        signal.alarm(current_timeout_seconds)

    def stopTest(self,current_test_case):
        signal.alarm(0)
        super().stopTest(current_test_case)

    def raise_test_timeout(self,current_signal_number,current_stack_frame):
        raise TimeoutError(f'회귀 테스트 {self.current_timeout_seconds}초 제한 초과')


def execute_regression_worker(current_test_modules, current_report_area, current_result_root):
    current_result_root = Path(current_result_root)
    current_start_clock = time.monotonic()
    current_stop_event = threading.Event()
    current_original_stdout,current_original_stderr = sys.stdout,sys.stderr
    current_exit_code = 1
    current_summary_record = {'status':'집계 불가'}
    with (current_result_root/'execution.log').open('w') as current_log_handle:
        sys.stdout = sys.stderr = current_log_handle
        def record_test_heartbeat():
            while not current_stop_event.wait(5):
                current_log_handle.write(f'{datetime.now().isoformat()}/{current_report_area}/heartbeat elapsed={time.monotonic()-current_start_clock:.1f}s log_bytes={current_log_handle.tell()}\n')
                current_log_handle.flush()
        current_heartbeat_thread = threading.Thread(target=record_test_heartbeat,daemon=True)
        current_heartbeat_thread.start()
        try:
            print(f'{datetime.now().isoformat()}/{current_report_area}/start',flush=True)
            current_test_suite = unittest.defaultTestLoader.loadTestsFromNames(current_test_modules)
            current_test_result = unittest.TextTestRunner(stream=current_log_handle,verbosity=2,resultclass=MusicRegressionResult).run(current_test_suite)
            current_exit_code = 0 if current_test_result.wasSuccessful() else 1
            current_summary_record = {'passed':current_test_result.testsRun-len(current_test_result.failures)-len(current_test_result.errors)-len(current_test_result.skipped),
                'failed':len(current_test_result.failures),'errors':len(current_test_result.errors),'skipped':len(current_test_result.skipped)}
            current_xml_root = ElementTree.Element('testsuite',tests=str(current_test_result.testsRun),failures=str(len(current_test_result.failures)),errors=str(len(current_test_result.errors)),skipped=str(len(current_test_result.skipped)))
            for current_error_kind,current_error_records in [('failure',current_test_result.failures),('error',current_test_result.errors)]:
                for current_test_case,current_error_text in current_error_records:
                    current_case_element = ElementTree.SubElement(current_xml_root,'testcase',name=current_test_case.id())
                    ElementTree.SubElement(current_case_element,current_error_kind).text = current_error_text
            ElementTree.ElementTree(current_xml_root).write(current_result_root/'junit.xml',encoding='unicode')
            if current_exit_code:
                current_summary_record['diagnostics'] = [{'test':current_test_case.id(),'error':current_error_text[-2200:]} for current_test_case,current_error_text in (current_test_result.failures+current_test_result.errors)[:8]]
        except BaseException:
            import traceback
            traceback.print_exc()
        finally:
            current_stop_event.set()
            current_heartbeat_thread.join()
            sys.stdout,sys.stderr = current_original_stdout,current_original_stderr
            current_summary_record.update(exit_code=current_exit_code,elapsed_seconds=round(time.monotonic()-current_start_clock,2),result_path=str(current_result_root))
            (current_result_root/'summary.json').write_text(json.dumps(current_summary_record,ensure_ascii=False,indent=2))
            (current_result_root/'exit-code').write_text(str(current_exit_code))
    print(json.dumps(current_summary_record,ensure_ascii=False))
    return current_exit_code


def create_regression_result_directory(current_report_area):
    current_report_root=WORKFLOW_ROOT_DIRECTORY/'.tmp/test'/current_report_area
    current_report_root.mkdir(parents=True,exist_ok=True)
    current_time_prefix=datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')+'_'
    return Path(tempfile.mkdtemp(prefix=current_time_prefix,dir=current_report_root))


def execute_music_regression(current_test_modules=MUSIC_REGRESSION_MODULES, current_report_area="music-regression"):
    """별도 프로세스의 종료 정리 출력까지 파일에 보존한다."""
    current_result_root = create_regression_result_directory(current_report_area)
    current_start_clock = time.monotonic()
    with (current_result_root/'runner.log').open('w') as current_runner_log:
        current_process_result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), '--worker', json.dumps(current_test_modules), current_report_area, str(current_result_root)],
            stdout=current_runner_log, stderr=subprocess.STDOUT,
        )
    try:
        current_summary_record = json.loads((current_result_root/'summary.json').read_text())
        if not isinstance(current_summary_record, dict) or current_summary_record.get('exit_code') != current_process_result.returncode:
            raise ValueError('작업자 종료 코드와 요약이 일치하지 않습니다.')
    except (OSError, ValueError) as current_report_error:
        current_summary_record = {'status':'집계 불가', 'reason':str(current_report_error),
            'exit_code':current_process_result.returncode, 'elapsed_seconds':round(time.monotonic()-current_start_clock,2), 'result_path':str(current_result_root)}
        (current_result_root/'summary.json').write_text(json.dumps(current_summary_record,ensure_ascii=False,indent=2))
    (current_result_root/'exit-code').write_text(str(current_process_result.returncode))
    print(json.dumps(current_summary_record,ensure_ascii=False))
    return current_process_result.returncode


if __name__=='__main__':
    if len(sys.argv) == 5 and sys.argv[1] == '--worker':
        sys.exit(execute_regression_worker(json.loads(sys.argv[2]), sys.argv[3], sys.argv[4]))
    sys.exit(execute_music_regression())
