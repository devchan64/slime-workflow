import os
from pathlib import Path
import subprocess
import tempfile
import unittest

class WanHistoryNavigationUiTests(unittest.TestCase):
    def test_service_dispatch_and_invalid_service(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'wan-history.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'WanVideoHistoryPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),Page=require(process.argv[1]).default;
              const cases={'wan22-i2v':'Wan 2.2 I2V','wan22-vace':'VACE','wan22-fun-control':'Fun Control','wan22-animate2':'Animate-2'};
              for(const [service,title] of Object.entries(cases)){global.location={search:'?service='+service+'&session=abc'};const html=server.renderToStaticMarkup(React.createElement(Page));assert.ok(html.includes(title));assert.ok(html.includes('/management/frame/'+service+'-generator/?session=abc'));assert.ok(html.includes('선택한 생성기의 이력과 삭제 범위만 표시합니다.'));}
              for(const service of ['invalid','constructor','toString','__proto__']){global.location={search:'?service='+service};assert.match(server.renderToStaticMarkup(React.createElement(Page)),/지원하지 않는 생성기/);}"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
