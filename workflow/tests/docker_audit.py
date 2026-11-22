"""비동기 Docker 전체 회귀 접수와 완료 보고서 조회."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / '.tmp/test/docker-audit'
IMAGE_FILES = (
    'requirements.txt', 'workflow/requirements.txt', 'generators/hermes_agent/requirements-mcp.lock',
    'gui/package.json', 'gui/package-lock.json',
)


def publish(path, record):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def submit():
    run = RUNS / uuid4().hex
    run.mkdir(parents=True, mode=0o700)
    report = run / 'report.json'
    record = dict(run_id=run.name, scope='all', status='queued', report_path=str(report))
    with (run / 'worker.lock').open('w') as lock, (run / 'runner.log').open('w') as log:
        fcntl.flock(lock, fcntl.LOCK_EX)
        publish(report, record)
        try:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), run.name],
                             start_new_session=True, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                             pass_fds=(lock.fileno(),))
        except OSError as error:
            record.update(status='error', reason=str(error), exit_code=1)
            publish(report, record)
    print(json.dumps(record, ensure_ascii=False))
    return record.get('exit_code', 0)


def result(run_id):
    if not re.fullmatch('[a-f0-9]{32}', run_id) or not (RUNS / run_id / 'report.json').is_file():
        print('등록된 회귀 실행 ID를 입력하세요.', file=sys.stderr)
        return 2
    run = RUNS / run_id
    with (run / 'worker.lock').open() as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            stopped = True
        except BlockingIOError:
            stopped = False
        report = run / 'report.json'
        record = json.loads(report.read_text())
        if stopped and record['status'] in ('queued', 'running'):
            record.update(status='error', reason='작업자가 최종 보고서 작성 전에 종료됐습니다.', exit_code=1)
            publish(report, record)
    print(json.dumps(record, ensure_ascii=False))
    return record.get('exit_code', 0)


def prepare_workspace(destination):
    for name in ('slime-workflow', 'slime-assets', 'slime-backend', 'slime-frontend'):
        repo = ROOT.parent / name
        files = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '--cached', '--others',
                                         '--exclude-standard', '-z']).split(b'\0')
        target = destination / name
        target.mkdir()
        for entry in filter(None, files):
            relative = Path(os.fsdecode(entry))
            source = repo / relative
            if not source.parent.resolve().is_relative_to(repo):
                raise ValueError(f'저장소 밖을 가리키는 경로: {name}/{relative}')
            if source.is_symlink():
                link = os.readlink(source)
                if os.path.isabs(link) or not source.resolve().is_relative_to(repo):
                    raise ValueError(f'저장소 밖을 가리키는 링크: {name}/{relative}')
            elif not source.is_file():
                continue
            output = target / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, output, follow_symlinks=False)
        subprocess.run(['git', 'init', '-q', str(target)], check=True)
        subprocess.run(['git', '-C', str(target), 'add', '-A'], check=True)
        subprocess.run(['git', '-C', str(target), '-c', 'user.name=Regression',
                        '-c', 'user.email=test@localhost', 'commit', '-qm', 'Regression snapshot'], check=True)

    # The pinned renderer distribution is gitignored but required by map tests.
    # Copy only the files named by the tracked manifest, after verifying each hash.
    import yaml
    relative = Path('gui/ui/map/vendor/field-renderer')
    source = ROOT / relative
    target = destination / 'slime-workflow' / relative
    manifest = yaml.safe_load((target / 'manifest.yaml').read_text())
    files = manifest.get('files') if isinstance(manifest, dict) else None
    if not isinstance(files, dict) or not files:
        raise ValueError('렌더러 manifest에 파일 목록이 없습니다.')
    for name, expected in files.items():
        if not isinstance(name, str) or Path(name).name != name or not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected):
            raise ValueError('렌더러 manifest 파일 또는 해시 형식 오류')
        path = source / name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'렌더러 배포 파일 누락 또는 해시 불일치: {name}')
        shutil.copy2(path, target / name)


def worker(run_id):
    run = RUNS / run_id
    report = run / 'report.json'
    record = json.loads(report.read_text())
    started = time.monotonic()
    try:
        record.update(status='running', runner_log=str(run / 'runner.log'))
        publish(report, record)
        with tempfile.TemporaryDirectory(dir=run) as scratch:
            work = Path(scratch)
            build = work / 'build'
            for name in IMAGE_FILES:
                (build / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, build / name)
            shutil.copyfile(ROOT / 'workflow/tests/docker/Dockerfile', build / 'Dockerfile')
            image_id = work / 'image-id'
            subprocess.run(['docker', 'build', '--iidfile', str(image_id), '-t', 'slime-workflow-audit:local',
                            str(build)], check=True)
            workspace = work / 'workspace'
            workspace.mkdir()
            prepare_workspace(workspace)
            project = workspace / 'slime-workflow'
            (project / '.venv').symlink_to('/opt/runtime')
            (project / '.local').mkdir(exist_ok=True)
            (project / '.local/hermes-mcp').symlink_to('/opt/hermes-mcp')
            (project / 'gui/node_modules').symlink_to('/opt/deps/gui/node_modules')
            artifacts = run / 'artifacts'
            artifacts.mkdir()
            command = ['docker', 'run', '--rm', '--init', '--network', 'none', '--user',
                       f'{os.getuid()}:{os.getgid()}', '-v', f'{workspace}:/workspace',
                       '-v', f'{artifacts}:/report', image_id.read_text().strip(),
                       'python', '-m', 'workflow.tests.docker_audit', '--inside']
            process = subprocess.run(command)
            if not (artifacts / 'summary.json').is_file():
                if process.returncode:
                    raise subprocess.CalledProcessError(process.returncode, 'docker run (summary.json 누락)')
                raise ValueError('컨테이너 종료 후 summary.json을 찾을 수 없습니다.')
            summary = json.loads((artifacts / 'summary.json').read_text())
            if summary.get('exit_code') != process.returncode or 'passed' not in summary:
                raise ValueError('회귀 작업자가 유효한 최종 집계를 반환하지 않았습니다.')
            record.update(summary, status='failed' if process.returncode else 'passed', result_path=str(artifacts))
    except Exception as error:
        record.update(status='error', reason=str(error), exit_code=getattr(error, 'returncode', 1))
    record['elapsed_seconds'] = round(time.monotonic() - started, 2)
    publish(report, record)
    return record['exit_code']


if __name__ == '__main__':
    if sys.argv[1:] == ['--inside']:
        from workflow.tests.run_management_audit import MANAGEMENT_AUDIT_MODULES
        from workflow.tests.run_music_regression import execute_regression_worker
        sys.exit(execute_regression_worker(MANAGEMENT_AUDIT_MODULES, 'management-audit', '/report'))
    sys.exit(worker(sys.argv[1]))
