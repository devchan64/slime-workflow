"""격리된 실제 이력 관측 결과와 공통 UI 페이지 계약을 연결한다."""
import json
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace

from workflow.common.generation_records import observe_generation_history_records


class GeneratorHistoryUiContractTests(unittest.TestCase):
    def test_thumbnail_retry_query_reaches_image_and_video_files(self):
        from workflow.domains.image.image_generation import ImageGenerationManager
        from workflow.common.reference_video_generation import ReferenceVideoGenerationManager
        identifier='2026-11-24_12-34-56-1234abcd';attempt='a'*32
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);job=root/identifier;video=job/'attempts'/attempt
            video.mkdir(parents=True);(job/'result.png').write_bytes(b'image');(video/'output-000.png').write_bytes(b'video-frame')
            image=ImageGenerationManager();image.job_storage_root=root
            video_manager=ReferenceVideoGenerationManager('/test-video',root,'unused',lambda value:value,lambda:None)
            for manager,path,expected in [(image,'/image-generation/jobs/'+identifier+'/result.png?retry=2',b'image'),
                                          (video_manager,'/test-video/jobs/'+identifier+'/attempts/'+attempt+'/output-000.png?retry=2',b'video-frame')]:
                handler=SimpleNamespace(path=path,command='GET',headers={'Host':'127.0.0.1:8770'},server=SimpleNamespace(server_port=8770),wfile=io.BytesIO(),status=None)
                handler.send_response=lambda status:setattr(handler,'status',status)
                handler.send_header=lambda *args:None
                handler.end_headers=lambda:None
                self.assertTrue(manager.handle_image_request(handler))
                self.assertEqual(handler.status,200)
                self.assertEqual(handler.wfile.getvalue(),expected)

    def test_thumbnail_distinguishes_unavailable_missing_and_pending(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'history.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'GeneratorHistory.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
              const Image=require(process.argv[1]).HistoryImage;
              const History=require(process.argv[1]).default;
              assert.equal(History({service:'wan22-i2v',resultId:'one'}).key,History({service:'wan22-i2v',resultId:'two'}).key);
              assert.notEqual(History({service:'wan22-i2v'}).key,History({service:'wan21-i2v'}).key);
              const render=(service,status,summary)=>server.renderToStaticMarkup(React.createElement(Image,{service,record:{id:'2026-11-24_12-34-56-1234abcd',recorded_status:status},summary}));
              assert.match(render('minimax-h3-image','completed',{}),/확인 불가/);
              assert.match(render('minimax-h3-image','completed',{image_available:false}),/이미지 없음/);
              assert.match(render('minimax-h3-image','running',{image_available:false}),/결과 준비 중/);
              assert.match(render('wan22-i2v','completed',{image_attempt:'invalid'}),/확인 불가/);
              assert.match(render('wan22-i2v','completed',{image_attempt:null}),/이미지 없음/);
              const refreshed=server.renderToStaticMarkup(React.createElement(Image,{service:'minimax-h3-image',record:{id:'2026-11-24_12-34-56-1234abcd',recorded_status:'completed'},summary:{image_available:true},revision:2}));
              assert.match(refreshed,/result.png\\?retry=2/);
              const Pagination=require(process.argv[1]).HistoryPagination;
              const page=(offset,next)=>({offset,next_offset:next,records:[{}],total:30});
              const pagination=(offset,next,query='')=>server.renderToStaticMarkup(React.createElement(Pagination,{page:page(offset,next),query,filter:'',pageSize:10,hintId:'hint',onPage:()=>{}}));
              assert.match(pagination(0,10),/첫 번째 이력 페이지/);assert.match(pagination(10,null),/마지막 이력 페이지/);
              assert.match(pagination(0,null),/표시할 다른 이력 페이지가 없습니다/);assert.match(pagination(10,20,'new'),/변경한 검색어/);
              assert.match(pagination(0,10),/aria-describedby="hint"/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

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
            script="""import {readFileSync} from 'node:fs';import vm from 'node:vm';import {untilAborted} from './gui/managementCommand.js';import {historyObserveRetry} from './gui/historyObserveRetry.mjs';import {validGeneratorHistoryPage} from './gui/generatorHistoryPage.mjs';
              const pages=JSON.parse(process.argv[1]),source=readFileSync('./gui/ActiveGeneratorProgress.jsx','utf8');
              const code=source.slice(source.indexOf('  useEffect(()=>{\\n    let active=true,deadline;'),source.indexOf('  const activeSummary='));
              let error='',records=null,calls=0;
              const context=vm.createContext({AbortController,untilAborted,historyObserveRetry,validGeneratorHistoryPage,document:{activeElement:null},refreshRef:{current:{}},restoreFocus:{current:false},jobRefs:{current:new Map()},refreshLock:{current:false},service:'service',revision:0,refreshKey:0,useEffect:fn=>fn(),setTimeout:()=>1,clearTimeout:()=>{},setLoading:()=>{},setError:value=>error=value,setRecords:value=>records=value,setTruncated:()=>{},setCheckedAt:()=>{},managementCommand:async()=>pages[calls++]});
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
