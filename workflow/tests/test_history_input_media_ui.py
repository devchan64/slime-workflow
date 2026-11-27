import os
from pathlib import Path
import subprocess
import tempfile
import unittest

class HistoryInputMediaUiTests(unittest.TestCase):
    def test_saved_media_thumbnails_and_untrusted_url(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'preview.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'HistoryInputPreview.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),Preview=require(process.argv[1]).default;
            const prefix='/management/assistant/vace-input/2026-11-24_11-17-24-15f79014/';
            const html=server.renderToStaticMarkup(React.createElement(Preview,{request:{images:[prefix+'reference'],edit_video:prefix+'edit_video'}}));
            assert.ok(html.includes('src="'+prefix+'reference"'));assert.ok(html.includes('src="'+prefix+'edit_video"'));
            const bad=server.renderToStaticMarkup(React.createElement(Preview,{request:{images:['https://example.com/image.png'],edit_video:'https://example.com/video.mp4'}}));
            assert.ok(!bad.includes('src="https://example.com/'));assert.ok(bad.includes('미리보기를 불러올 수 없습니다.'));
            const badVideo=server.renderToStaticMarkup(React.createElement(Preview,{request:{pose_video:'https://example.com/video.mp4'}}));
            assert.ok(badVideo.includes('포즈 영상'));assert.ok(badVideo.includes('미리보기를 불러올 수 없습니다.'));assert.ok(!badVideo.includes('src="https://example.com/'));"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
