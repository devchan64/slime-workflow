"""헤르메스 이력 서비스와 화면의 페이지 계약 호환성."""
import json
from pathlib import Path
import subprocess
import unittest

from workflow.domains.hermes_agent.audio_operations import sanitize_hermes_source_history


class SourceHistoryFrontendTests(unittest.TestCase):
    def test_history_services_distinguish_archived_and_current_profiles(self):
        import tempfile
        from fastapi.testclient import TestClient
        from http.server import SimpleHTTPRequestHandler
        from workflow.common.management_asgi import build_management_application
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with TestClient(app) as client:
                response=client.get('/management/assistant/history-services')
        self.assertEqual(response.status_code,200)
        rows={row['service']:row for row in response.json()}
        for service in ('seamless-tile','floor-tile','qwen-21','music-minimax'):
            self.assertTrue(rows[service]['archived']);self.assertIn(rows[service]['result_kind'],('image','audio'))
        for service in ('flux-seamless','flux-image','music-heartmula'):
            self.assertFalse(rows[service]['archived'])
        self.assertTrue(rows['character-animation']['archived'])
        self.assertEqual(rows['character-animation']['result_kind'],'character')
        root=Path(__file__).resolve().parents[2]
        script="""import {validRecentHistorySource,selectRecentHistorySources} from './gui/recentHistorySource.mjs';
          const sources=JSON.parse(process.argv[1]);for(const source of sources)if(!validRecentHistorySource(source))throw Error(source.service);
          if(!selectRecentHistorySources(sources).length)throw Error('no sources');
          for(const bad of [[],[{...sources[0],command:'unsupported'}],[sources[0],sources[0]]]){let failed=false;try{selectRecentHistorySources(bad)}catch{failed=true}if(!failed)throw Error('bad source list accepted');}"""
        result=subprocess.run(['node','--input-type=module','-e',script,json.dumps(response.json())],cwd=root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_real_sanitized_pages_are_accepted_for_image_video_and_audio(self):
        root=Path(__file__).resolve().parents[2]
        source={'records':[{'id':'job-1','recorded_status':'completed','status_source':'job'}],
                'total':1,'offset':0,'next_offset':None,'snapshot':'a'*64,'unavailable_count':0}
        pages=[sanitize_hermes_source_history(service,{'offset':0,'limit':10},source)
               for service in ('flux-image','wan22-fun-control','music-heartmula')]
        script="""import {validSourceHistoryPage} from './gui/sourceHistoryPage.mjs';
          import {validRecentHistoryPage} from './gui/recentHistorySource.mjs';
          const pages=JSON.parse(process.argv[1]);
          for(const page of pages){if(!validSourceHistoryPage(page,page.service,0) || !validRecentHistoryPage(page,page.service))throw Error(page.service);
            for(const count of [-1,'0',null])if(validRecentHistoryPage({...page,unavailable_count:count},page.service))throw Error('bad unavailable count');}"""
        result=subprocess.run(['node','--input-type=module','-e',script,json.dumps(pages)],cwd=root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
