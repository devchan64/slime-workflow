"""격리된 Fun Control 저장 입력 응답과 UI 검증의 계약을 확인한다."""
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class FunSavedInputUiContractTests(unittest.TestCase):
    def test_isolated_saved_pose_response_is_accepted_by_ui(self):
        import cv2
        import numpy as np
        from PIL import Image
        from fastapi.testclient import TestClient
        from http.server import SimpleHTTPRequestHandler
        from workflow.common.management_asgi import build_management_application

        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            job='2026-11-18_00-00-00-12345678'
            folder=root/job
            folder.mkdir()
            video=folder/'pose-input.mp4'
            writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'mp4v'),16,(832,480))
            self.assertTrue(writer.isOpened())
            for _ in range(5):
                writer.write(np.zeros((480,832,3),dtype=np.uint8))
            writer.release()
            Image.new('RGB',(832,480),'white').save(folder/'reference-1.png')
            saved={'action':'generate','prompt':'walking','negative_prompt':'','control_type':'pose','width':832,'height':480,'frames':5,'steps':20,'seed':42,'flow_shift':5,'guidance_scale':6,'switch_ratio':.5,'pose_video_file':'pose-input.mp4','references':['reference-1.png']}
            (folder/'request.json').write_text(json.dumps(saved))
            app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with patch('workflow.domains.hermes_agent.video_operations.make_hermes_video_source_manager',return_value=SimpleNamespace(job_storage_root=root)),TestClient(app) as client:
                response=client.get('/management/assistant/fun-input/'+job)
            self.assertEqual(response.status_code,200,response.text)
            script="""const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
              const source=fs.readFileSync('gui/FunControlPage.jsx','utf8');
              const code=source.slice(source.indexOf('function validFunInput('),source.indexOf('export function validFunForm('));
              const c=vm.createContext({});vm.runInContext(code+';this.valid=validFunInput;',c);
              const value=JSON.parse(fs.readFileSync(0,'utf8'));assert.equal(c.valid(value,value.id,{saved:true}),true);
              assert.equal(c.valid({...value,request:{...value.request,images:[]}},value.id,{saved:true}),false);"""
            subprocess.run(['node','-e',script],cwd=Path(__file__).resolve().parents[2],input=json.dumps(response.json()),text=True,check=True,capture_output=True)


if __name__=='__main__':
    unittest.main()
