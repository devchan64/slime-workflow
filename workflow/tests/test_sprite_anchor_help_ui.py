"""스프라이트 앵커 이력 동작 설명의 렌더를 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class SpriteAnchorHelpTests(unittest.TestCase):
    def test_help_distinguishes_history_and_source(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'sprite.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'SpriteAnchorRestore.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),render=require('react-dom/server').renderToStaticMarkup,assert=require('node:assert/strict');
const html=render(React.createElement(require(process.argv[1]).SpriteAnchorRestoreHelp));
assert.match(html,/별도 이력/);assert.match(html,/편집표에 적용/);assert.match(html,/원본 에셋을 변경하지 않습니다/);
const Expired=require(process.argv[1]).SpriteAnchorRestoreExpired,rows=[];
assert.equal(render(React.createElement(Expired,{review:null,rows})), '');
assert.equal(render(React.createElement(Expired,{review:{before:rows},rows})), '');
const stale=render(React.createElement(Expired,{review:{before:[]},rows}));
assert.match(stale,/role="status"/);assert.match(stale,/복원 검토가 만료/);
const identity=require(process.argv[1]).spriteAnchorSourceIdentity;
const source={source:'registered',path:'sheet.png',imageSha256:'image',metadataSha256:'first',animation:{animationId:'walk',version:'v1'}};
assert.equal(identity(source),identity({...source}));
assert.notEqual(identity(source),identity({...source,metadataSha256:'second'}));
assert.notEqual(identity(source),identity({...source,source:'baseline'}));"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
