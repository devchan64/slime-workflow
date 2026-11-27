"""서버가 구성한 빌보드 페이지와 UI 페이지 검증의 연결을 확인한다."""
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.asset_observer import read_hermes_billboard_catalog


class BillboardCatalogUiContractTests(unittest.TestCase):
    def test_server_page_uses_gallery_without_local_filter_or_pagination(self):
        import os, tempfile
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'gallery.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'CardGallery.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),assert=require('node:assert/strict'),Gallery=require(process.argv[1]).default;
            const items=Array.from({length:10},(_,i)=>({id:'asset-'+i,label:'에셋 '+i,description:'식생'}));
            const html=server.renderToStaticMarkup(React.createElement(Gallery,{items,selected:'asset-0',label:'빌보드',imageUrl:item=>'/image/'+item.id,onSelect:()=>{},external:{disabledItem:item=>item.id!=='asset-0',disabledReasonId:'locked',emptyMessage:'없음'}}));
            assert.equal((html.match(/aria-pressed=/g)||[]).length,10);assert.match(html,/aria-pressed="true"/);assert.match(html,/aria-describedby="locked"/);assert.match(html,/식생/);assert.doesNotMatch(html,/type="search"|페이지 이동/);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_observed_pages_are_accepted_by_ui(self):
        assets = [
            {'texture':f'test-{index}', 'name':f'나무 {index}', 'category':'vegetation',
             'modeling':{'purpose':'배경'}, 'maps':[{'path':'assets/maps/field.yaml','texture_key_occurrences':index}]}
            for index in range(12)
        ]
        requests = [{'offset':0,'limit':10}, {'offset':10,'limit':10}, {'offset':0,'limit':10,'query':'없는 항목'}]
        with patch('workflow.common.management_gateway.execute_management_command', return_value={'assets':assets, 'revision':'a'*64}):
            pages = [read_hermes_billboard_catalog(request) for request in requests]
        script = """import {validBillboardCatalogPage as valid} from './gui/billboardCatalogPage.mjs';
          const chunks=[]; for await(const chunk of process.stdin)chunks.push(chunk);
          const {pages,requests}=JSON.parse(Buffer.concat(chunks));
          if(!pages.every((page,index)=>valid(page,requests[index])))process.exit(1);"""
        root = Path(__file__).resolve().parents[2]
        subprocess.run(['node','--input-type=module','-e',script], cwd=root, input=json.dumps({'pages':pages,'requests':requests}), text=True, check=True)


if __name__ == '__main__':
    unittest.main()
