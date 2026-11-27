import os
from pathlib import Path
import subprocess
import tempfile
import unittest

class ImageHistoryContextUiTests(unittest.TestCase):
    def test_flux_session_and_building_form_are_retained(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            for source in ('FluxHistoryPage.jsx','MiniMaxImageHistoryPage.jsx'):
                bundle=Path(directory)/(source+'.cjs')
                subprocess.run([str(gui/'node_modules/.bin/esbuild'),source,'--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
                if source.startswith('Flux'):
                    script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');global.location={search:'?service=flux-building&session=abc'};const {default:Page,fluxHistoryUrl:url}=require(process.argv[1]);const html=server.renderToStaticMarkup(React.createElement(Page));assert.ok(html.includes('/management/frame/flux-building-generator/?session=abc'));assert.equal(url('flux-building','bad','abc'),'/management/frame/flux-image-history/?service=flux-building&session=abc');"""
                else:
                    script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');global.location={search:'?form=building&session=abc'};const {default:Page,minimaxImageHistoryUrl:url}=require(process.argv[1]);const html=server.renderToStaticMarkup(React.createElement(Page));assert.ok(html.includes('/management/frame/minimax-h3-building-generator/?session=abc'));assert.equal(url(true,undefined,'abc'),'/management/frame/minimax-h3-image-history/?form=building&session=abc');"""
                subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
