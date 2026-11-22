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

    def test_real_sanitized_pages_are_accepted_for_image_video_and_audio(self):
        root=Path(__file__).resolve().parents[2]
        source={'records':[{'id':'job-1','recorded_status':'completed','status_source':'job'}],
                'total':1,'offset':0,'next_offset':None,'snapshot':'a'*64,'unavailable_count':0}
        pages=[sanitize_hermes_source_history(service,{'offset':0,'limit':10},source)
               for service in ('flux-image','wan22-fun-control','music-heartmula')]
        script="""import {validSourceHistoryPage} from './gui/sourceHistoryPage.mjs';
          const pages=JSON.parse(process.argv[1]);
          for(const page of pages) if(!validSourceHistoryPage(page,page.service,0)) throw Error(page.service);"""
        result=subprocess.run(['node','--input-type=module','-e',script,json.dumps(pages)],cwd=root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
