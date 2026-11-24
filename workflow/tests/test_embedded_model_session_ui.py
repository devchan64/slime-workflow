"""대화 내 모델 관리 링크가 현재 세션을 유지하는지 확인한다."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class EmbeddedModelSessionUI(unittest.TestCase):
    def test_embedded_generators_use_conversation_session(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        pages=[('DwposePage.jsx','default'),('VacePage.jsx','default'),
               ('I2VPage.jsx','default'),('Wan21VideoPage.jsx','Wan21T2VPage'),
               ('Wan21VideoPage.jsx','Wan21I2VPage'),
               ('FunControlPage.jsx','default'),('SoundEffectPage.jsx','default'),
               ('SoundEffectPage.jsx','HeartmulaPage'),('TranslationPage.jsx','default'),('WriterPage.jsx','default')]
        script="""global.location={pathname:'/management/assistant/',search:'?session=old',href:'http://localhost/management/assistant/?session=old'};
          global.sessionStorage={getItem:()=>null};
          const React=require('react'),server=require('react-dom/server');
          const Page=require(process.argv[1])[process.argv[2]];
          process.stdout.write(server.renderToStaticMarkup(React.createElement(Page,{embedded:true,session:'new'})));"""
        with tempfile.TemporaryDirectory() as directory:
            bundles={}
            for filename,export in pages:
                with self.subTest(page=filename,export=export):
                    if filename not in bundles:
                        bundle=Path(directory)/(filename+'.cjs')
                        subprocess.run([str(gui/'node_modules/.bin/esbuild'),filename,'--bundle','--platform=node',
                                        '--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
                        bundles[filename]=bundle
                    markup=subprocess.check_output(['node','-e',script,str(bundles[filename]),export],cwd=gui,text=True,
                                                   env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
                    self.assertRegex(markup,r'/management/frame/model-management/\?model=[^"&]+&amp;session=new')
                    self.assertNotRegex(markup,r'/management/frame/model-management/\?model=[^"&]+&amp;session=old')
