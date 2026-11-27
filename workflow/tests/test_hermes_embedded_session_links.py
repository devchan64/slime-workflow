"""대화 내장 생성기에서 현재 세션 복귀 링크를 유지한다."""
import os
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


class EmbeddedSessionLinksTests(unittest.TestCase):
    def test_handoff_service_status_matches_frontend_identity_contract(self):
        from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore, _canonical_input
        from workflow.domains.hermes_agent.service import HermesServiceManager
        from workflow.domains.hermes_agent.session_store import HermesSessionStore
        root=Path(__file__).resolve().parents[2]
        session='a'*32; identifier='request_123'; service='flux-image'
        request={'prompt':'test','steps':16}
        with tempfile.TemporaryDirectory() as directory:
            temporary=Path(directory)
            sessions=HermesSessionStore(temporary/'sessions'); sessions.create_session_record(session)
            handoffs=GpuHandoffStore(temporary/'handoffs')
            handoffs.approve(identifier,session,service,hashlib.sha256(_canonical_input(request)).hexdigest(),
                             target_request=request,resident_id='resident_123',confirmed=True)
            manager=HermesServiceManager(hermes_storage_root=temporary/'jobs',hermes_session_root=temporary/'sessions')
            with patch('workflow.domains.hermes_agent.gpu_handoff_store.GpuHandoffStore',return_value=handoffs):
                found=manager.execute_hermes_command('hermes-gpu-handoff-status',{'session_id':session,'request_id':identifier})
                missing=manager.execute_hermes_command('hermes-gpu-handoff-status',{'session_id':session,'request_id':'missing_123'})
            self.assertNotIn('target_request',found)
            self.assertEqual(found['target_summary']['prompt'],'test')
            script="""import {validateGpuHandoffStatus} from './gui/validateGpuHandoffStatus.mjs';
              const [found,missing]=JSON.parse(process.argv[1]);
              validateGpuHandoffStatus(found,process.argv[2],'request_123','flux-image');
              validateGpuHandoffStatus(missing,process.argv[2],'missing_123','flux-image');"""
            result=subprocess.run(['node','--input-type=module','-e',script,json.dumps([found,missing]),session],cwd=root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_audio_generators_keep_session_without_reloading_embedded_panel(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'audio.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'SoundEffectPage.jsx','--bundle','--platform=node',
                            '--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""global.location={search:'?session=old'};global.sessionStorage={getItem:()=>null};
              const React=require('react'),server=require('react-dom/server'),pages=require(process.argv[1]);
              for(const Page of [pages.default,pages.HeartmulaPage]){
                const embedded=server.renderToStaticMarkup(React.createElement(Page,{embedded:true,session:'new'}));
                const standalone=server.renderToStaticMarkup(React.createElement(Page,{session:'new'}));
                if(embedded.includes('/management/assistant/?session='))throw Error('내장 패널은 대화 페이지를 다시 열지 않아야 합니다');
                if(!standalone.includes('/management/assistant/?session=new') || standalone.includes('/management/assistant/?session=old'))throw Error(standalone);
              }"""
            result=subprocess.run(['node','-e',script,str(bundle)],cwd=gui,capture_output=True,text=True,
                                  env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
            self.assertEqual(result.returncode,0,result.stderr)
