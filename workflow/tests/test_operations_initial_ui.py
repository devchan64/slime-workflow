"""운영 작업 화면의 첫 조회 안내를 렌더링해 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class OperationsInitialUiTests(unittest.TestCase):
    def test_initial_render_explains_manual_observation(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'operations.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'OperationsJobs.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """globalThis.sessionStorage={getItem:()=>null,setItem:()=>{}};
const React=require('react'),render=require('react-dom/server').renderToStaticMarkup,assert=require('node:assert/strict');
const Page=require(process.argv[1]).default;
const html=render(React.createElement(Page,{session:'test'}));
assert.match(html,/전체 상태로 작업 조회를 누르세요/);
assert.match(html,/GPU 대기열과 예약은 조회 버튼을 눌러 확인할 수 있습니다/);
assert.doesNotMatch(html,/조회된 작업이 없습니다/);
const Status=require(process.argv[1]).OperationsRefreshStatus;
for(const label of ['운영 작업 목록','GPU 관측']){
const status=render(React.createElement(Status,{loading:true,hasPrevious:true,label}));
assert.match(status,/role="status"/);assert.match(status,/마지막 조회 결과/);
assert.equal(render(React.createElement(Status,{loading:false,hasPrevious:true,label})), '');
assert.equal(render(React.createElement(Status,{loading:true,hasPrevious:false,label})), '');
}
const Pagination=require(process.argv[1]).OperationsPagination;
const top=render(React.createElement(Pagination,{position:'위',canPrevious:false,canNext:true}));
const bottom=render(React.createElement(Pagination,{position:'아래',canPrevious:true,canNext:false}));
assert.match(top,/aria-label="운영 작업 페이지 이동 · 목록 위"/);assert.match(bottom,/aria-label="운영 작업 페이지 이동 · 목록 아래"/);
assert.match(top,/class="ui-action-row"/);assert.match(top,/disabled="">이전 페이지/);assert.match(bottom,/disabled="">다음 페이지/);"""
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True, capture_output=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
