import os
from pathlib import Path
import subprocess
import tempfile
import unittest

class MiniMaxVideoHistoryNavigationUiTests(unittest.TestCase):
    def test_session_is_kept_in_history_and_input_links(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'history.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'MiniMaxVideoHistoryPage.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict');
              global.location={search:'?service=minimax-h3-ref2va&session=session123'};
              const {default:Page,miniMaxVideoHistoryUrl:url}=require(process.argv[1]);
              const html=server.renderToStaticMarkup(React.createElement(Page));
              assert.ok(html.includes('/management/frame/minimax-h3-ref2va-generator/?session=session123'));
              assert.equal(url('minimax-h3-i2v','2026-11-26_22-23-35-f13c417b','session123'),'/management/frame/minimax-h3-video-history/?service=minimax-h3-i2v&session=session123&job=2026-11-26_22-23-35-f13c417b');"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
