"""콘텐츠 상태의 알 수 없는 값 표시를 확인한다."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest


class ContentStatusUiTests(unittest.TestCase):
    def test_receipt_hash_help_is_unique_and_connected(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'receipt.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'MapDatabaseReceipt.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),{default:Receipt,validMapReceiptId:valid}=require(process.argv[1]);
              const html=server.renderToStaticMarkup(React.createElement(React.Fragment,null,React.createElement(Receipt),React.createElement(Receipt)));
              const ids=[...html.matchAll(/<input[^>]*aria-describedby="([^"]+)"/g)].map(match=>match[1]);assert.equal(ids.length,4);assert.equal(new Set(ids).size,4);
              for(const id of ids)assert.ok(html.includes('id="'+id+'"'));
              assert.equal(valid(''),false);assert.equal(valid('😀'.repeat(180)),true);assert.equal(valid('😀'.repeat(181)),false);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_initial_status_button_describes_loading(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'status.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'ContentDatabaseStatus.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),Page=require(process.argv[1]).default;
              const html=server.renderToStaticMarkup(React.createElement(Page));
              const id=html.match(/disabled="" aria-describedby="([^"]+)">조회 중/)[1];
              assert.ok(html.includes('id="'+id+'" role="status">콘텐츠 DB 상태 조회 중'));"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_unrecognized_values_never_become_object_properties(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'status.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'ContentDatabaseStatus.jsx','--bundle','--platform=node','--format=cjs','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const assert=require('node:assert/strict'),{contentStatusLabel:label}=require(process.argv[1]);
              assert.equal(label('mode','database'),'DB');assert.equal(label('source','matched'),'일치');assert.equal(label('save','pending'),'중단 기록 확인 필요');
              for(const kind of ['mode','source','save','toString'])for(const value of ['toString','constructor',null,{}])assert.equal(label(kind,value),'확인 불가');"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True)
