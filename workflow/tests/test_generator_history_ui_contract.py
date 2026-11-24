"""격리된 실제 이력 관측 결과와 공통 UI 페이지 계약을 연결한다."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from workflow.common.generation_records import observe_generation_history_records


class GeneratorHistoryUiContractTests(unittest.TestCase):
    def test_active_progress_is_keyed_by_service_not_revision(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'progress.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'ActiveGeneratorProgress.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const assert=require('node:assert/strict'),Progress=require(process.argv[1]).default;
              assert.equal(Progress({service:'wan22-i2v',revision:1}).key,Progress({service:'wan22-i2v',revision:2}).key);
              assert.notEqual(Progress({service:'wan22-i2v'}).key,Progress({service:'wan21-i2v'}).key);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True)

    def test_active_progress_accepts_actual_observed_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);history=root/'history';jobs=root/'jobs';history.mkdir();jobs.mkdir()
            for index in range(31):
                job=jobs/f'2026-11-18_12-00-00-{index:08x}';job.mkdir()
                (job/'request.json').write_text('{}');(job/'status.json').write_text('{"status":"completed"}')
            first=observe_generation_history_records(history,jobs,{'limit':30})
            last=observe_generation_history_records(history,jobs,{'limit':30,'offset':first['next_offset'],'snapshot':first['snapshot']})
            script="""import {readFileSync} from 'node:fs';import vm from 'node:vm';import {untilAborted} from './gui/managementCommand.js';import {validGeneratorHistoryPage} from './gui/generatorHistoryPage.mjs';
              const pages=JSON.parse(process.argv[1]),source=readFileSync('./gui/ActiveGeneratorProgress.jsx','utf8');
              const code=source.slice(source.indexOf('  useEffect(()=>{\\n    let active=true,deadline;'),source.indexOf('  const activeSummary='));
              let error='',records=null,calls=0;
              const context=vm.createContext({AbortController,untilAborted,validGeneratorHistoryPage,document:{activeElement:null},refreshRef:{current:{}},restoreFocus:{current:false},jobRefs:{current:new Map()},refreshLock:{current:false},service:'service',revision:0,refreshKey:0,useEffect:fn=>fn(),setTimeout:()=>1,clearTimeout:()=>{},setLoading:()=>{},setError:value=>error=value,setRecords:value=>records=value,setTruncated:()=>{},setCheckedAt:()=>{},managementCommand:async()=>pages[calls++]});
              vm.runInContext(code,context);await new Promise(done=>setImmediate(done));
              if(error || !Array.isArray(records) || records.length || calls!==2)throw Error(error || 'page rejected');"""
            subprocess.run(['node','--input-type=module','-e',script,json.dumps([first,last])],cwd=Path(__file__).resolve().parents[2],check=True,capture_output=True,text=True)

    def test_observed_pages_are_accepted_and_corrupt_next_offset_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history, jobs = root / 'history', root / 'jobs'
            history.mkdir()
            jobs.mkdir()
            for index in range(3):
                job = jobs / f'2026-11-18_12-0{index}-00-{index:08x}'
                job.mkdir()
                (job / 'request.json').write_text(json.dumps({'prompt': 'isolated'}))
                (job / 'status.json').write_text(json.dumps({'status': 'completed'}))
            first = observe_generation_history_records(history, jobs, {'limit': 2})
            last = observe_generation_history_records(history, jobs, {
                'limit': 2, 'offset': first['next_offset'], 'snapshot': first['snapshot']})
            empty = observe_generation_history_records(history, jobs, {'limit': 2, 'query': 'missing'})
            cases = [[first, 0, 2, None, True], [last, 2, 2, first['snapshot'], True],
                     [empty, 0, 2, None, True], [{**first, 'next_offset': 3}, 0, 2, None, False]]
            script = """
              import assert from 'node:assert/strict';
              import {validGeneratorHistoryPage} from './gui/generatorHistoryPage.mjs';
              let data=''; for await (const part of process.stdin) data+=part;
              for (const [page,offset,limit,snapshot,expected] of JSON.parse(data))
                assert.equal(validGeneratorHistoryPage(page,offset,limit,snapshot),expected);
            """
            subprocess.run(['node', '--input-type=module', '-e', script],
                           input=json.dumps(cases), text=True, check=True,
                           cwd=Path(__file__).resolve().parents[2], capture_output=True)


if __name__ == '__main__':
    unittest.main()
