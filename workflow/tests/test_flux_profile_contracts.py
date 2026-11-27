"""현행 FLUX 프로필의 요청과 저장 이력 복원 계약."""
import base64
import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from workflow.common.reference_restore import HistoryInputError
from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
from workflow.domains.image.flux_image_generation import FluxImageGenerationManager
from workflow.domains.image.flux_input_restore import restore_flux_image_inputs
from workflow.domains.image.three_reference_generation import save_three_reference_inputs


class FluxProfileContracts(unittest.TestCase):
    def test_delete_one_profile_preserves_same_id_in_other_profile(self):
        import json
        from itertools import product
        from unittest.mock import patch
        from workflow.domains.image.flux_expression_generation import FluxExpressionGenerationManager
        with tempfile.TemporaryDirectory() as directory, patch('workflow.domains.image.flux_image_generation.MANAGER_HISTORY_ROOT', Path(directory)/'history'), patch('workflow.domains.image.flux_expression_generation.MANAGER_HISTORY_ROOT', Path(directory)/'history'):
            root=Path(directory); job_id='2026-11-27_00-00-00-1234abcd'
            managers={profile:FluxImageGenerationManager(profile) for profile in FLUX_IMAGE_PROFILE_RECORDS}
            managers['flux-expression']=FluxExpressionGenerationManager()
            for (profile,manager),action in product(managers.items(),('selected','all')):
                with self.subTest(profile=profile,action=action):
                    for other_profile,other in managers.items():
                        other.job_storage_root=root/other_profile
                        job=other.job_storage_root/job_id; job.mkdir(parents=True,exist_ok=True)
                        (job/'status.json').write_text('{"status":"completed"}')
                        (job/'result.png').write_bytes(b'image')
                        other.history_storage_path().mkdir(parents=True,exist_ok=True)
                        (other.history_storage_path()/(job_id+'.json')).write_text(json.dumps({'id':job_id}))
                    if action=='selected':
                        manager.delete_generation_history(job_id)
                    else:
                        preview=manager.preview_generation_cleanup()
                        manager.reset_generation_history(preview['jobs'])
                    self.assertFalse((manager.job_storage_root/job_id).exists())
                    self.assertFalse((manager.history_storage_path()/(job_id+'.json')).exists())
                    for other_profile,other in managers.items():
                        if other_profile==profile: continue
                        self.assertTrue((other.job_storage_root/job_id/'result.png').is_file(),other_profile)
                        self.assertTrue((other.history_storage_path()/(job_id+'.json')).is_file(),other_profile)

    def test_proposal_session_is_kept_in_standalone_and_embedded_links(self):
        import os
        import subprocess
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'flux-page.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'FluxImagePage.jsx','--bundle','--platform=node',
                            '--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""global.location={pathname:'/management/assistant/',search:'?session=old'};
              global.sessionStorage={getItem:()=>null};
              const React=require('react'),server=require('react-dom/server');
              const Page=require(process.argv[1]).default;
              const Feedback=require(process.argv[1]).FluxToolFeedback;
              const assert=require('node:assert/strict');
              assert.equal(Page({serviceOverride:'flux-image',receiptScope:{job:'one'}}).key,Page({serviceOverride:'flux-image',receiptScope:{job:'two'}}).key);
              assert.notEqual(Page({serviceOverride:'flux-image'}).key,Page({serviceOverride:'flux-prop'}).key);
              const render=props=>server.renderToStaticMarkup(React.createElement(Feedback,props));
              assert.match(render({loading:true}),/role="status"/);assert.match(render({notice:'완료'}),/role="status"/);
              assert.match(render({notice:'실패',error:true}),/role="alert"/);
              const Pagination=require(process.argv[1]).FluxGuidePagination;
              const page=(count,page)=>server.renderToStaticMarkup(React.createElement(Pagination,{count,page,pageSize:8,hintId:'hint',onMove:()=>{}}));
              assert.match(page(0,0),/검색 결과가 없어/);assert.match(page(4,0),/다른 가이드 페이지가 없습니다/);
              assert.match(page(9,0),/첫 번째 가이드 페이지/);assert.match(page(9,1),/마지막 가이드 페이지/);assert.match(page(9,0),/aria-describedby="hint"/);
              const props={serviceOverride:'flux-image',receiptScope:{session:'new',job:'proposal'}};
              const standalone=server.renderToStaticMarkup(React.createElement(Page,props));
              assert.ok(standalone.includes('/management/assistant/?session=new'));
              assert.ok(!standalone.includes('/management/assistant/?session=old'));
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Page,{...props,embedded:true})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,
                                           env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertNotIn('aria-label="워크플로우 탐색"',markup)
        self.assertNotIn('/management/assistant/?session=old',markup)
        self.assertIn('/management/frame/model-management/?model=flux-image&amp;session=new',markup)

    def test_each_profile_has_a_distinct_react_menu_and_route(self):
        from http.server import SimpleHTTPRequestHandler
        from fastapi.testclient import TestClient
        from workflow.common.management_asgi import build_management_application
        from workflow.common.management_catalog import NATIVE_MANAGEMENT_APPLICATIONS, REACT_REVIEW_PATHS
        services=[*FLUX_IMAGE_PROFILE_RECORDS,'flux-expression']
        self.assertEqual(len(services),9)
        routes=[REACT_REVIEW_PATHS[service+'-generator'] for service in services]
        self.assertEqual(len(set(routes)),len(services))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            app=build_management_application(SimpleHTTPRequestHandler,root,root/'source.json',8770,[])
            with TestClient(app) as client:
                for service,route in zip(services,routes):
                    with self.subTest(service=service):
                        self.assertIn(service+'-generator',NATIVE_MANAGEMENT_APPLICATIONS)
                        response=client.get(route)
                        self.assertEqual(response.status_code,200,response.text[:200])
                        self.assertIn('/management/assistant/app.js',response.text)

    def test_all_profiles_restore_saved_inputs_and_reject_cross_profile(self):
        image=io.BytesIO(); Image.new('RGB',(16,16),'white').save(image,format='PNG')
        encoded=base64.b64encode(image.getvalue()).decode()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for index,(profile,record) in enumerate(FLUX_IMAGE_PROFILE_RECORDS.items()):
                with self.subTest(profile=profile):
                    job=f'2026-11-22_00-00-0{index}-12345678'; path=root/job; path.mkdir()
                    references=[encoded] if record[4] else []
                    payload={'action':'generate','prompt':'A small blue object','width':512,'height':512,'steps':16,'seed':42,'images':references,'tag':''}
                    manager=FluxImageGenerationManager(profile)
                    saved=save_three_reference_inputs(path,manager.validate_generation_request(payload))
                    restored=restore_flux_image_inputs({'id':job,'request':saved},profile,root)
                    self.assertEqual(restored[0],'A small blue object')
                    self.assertEqual(restored[3:7],(512,512,16,42))
                    self.assertEqual(restored[1] is not None,bool(references))
                    wrong='flux-prop' if profile!='flux-prop' else 'flux-image'
                    with self.assertRaises(HistoryInputError):
                        restore_flux_image_inputs({'id':job,'request':saved},wrong,root)
                    with self.assertRaises(HistoryInputError):
                        restore_flux_image_inputs({'id':job,'request':{**saved,'prompt':'changed'}},profile,root)
                    if profile!='flux-character':
                        with self.assertRaises(HistoryInputError):
                            restore_flux_image_inputs({'id':job,'request':{**saved,'steps':4}},profile,root)

    def test_required_references_and_seamless_restrictions(self):
        for profile,record in FLUX_IMAGE_PROFILE_RECORDS.items():
            if not record[4]: continue
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                FluxImageGenerationManager(profile).validate_generation_request({'action':'generate','prompt':'object','width':512,'height':512,'steps':16,'seed':42,'images':[]})
        base={'action':'generate','prompt':'grass','width':512,'height':512,'steps':16,'seed':42,'images':[]}
        seamless=FluxImageGenerationManager('flux-seamless')
        self.assertEqual(seamless.validate_generation_request(base)['seamless_method'],'global-periodic-v1')
        for change in ({'width':768},{'steps':4}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                seamless.validate_generation_request({**base,**change})
