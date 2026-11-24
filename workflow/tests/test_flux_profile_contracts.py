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
    def test_embedded_proposal_return_link_uses_its_session(self):
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
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Page,{serviceOverride:'flux-image',embedded:true,receiptScope:{session:'new',job:'proposal'}})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,
                                           env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('/management/assistant/?session=new',markup)
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
