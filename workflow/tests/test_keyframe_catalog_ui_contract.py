"""키프레임 목록 서버와 GUI 페이지 검증의 연결을 확인한다."""
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.keyframe_observer import read_hermes_kimodo_keyframe_catalog


class KeyframeCatalogUiContractTests(unittest.TestCase):
    def test_observed_first_last_and_empty_pages(self):
        records=[{'id':f'{index:032x}','tag':f'자세 {index}','source_frame':index+1} for index in range(21)]
        with patch('workflow.domains.hermes_agent.keyframe_observer.execute_management_command',return_value={'records':records}):
            first=read_hermes_kimodo_keyframe_catalog({'query':'','limit':20})
            cursor={'offset':20,'snapshot':first['snapshot']}
            last=read_hermes_kimodo_keyframe_catalog({'query':'','limit':20,**cursor})
            empty=read_hermes_kimodo_keyframe_catalog({'query':'없는 자세','limit':20})
        script="""import {validKeyframeCatalogPage as valid} from './gui/keyframeCatalogPage.mjs';let data='';for await(const part of process.stdin)data+=part;
          const {pages,cursors}=JSON.parse(data);if(!pages.every((page,index)=>valid(page,cursors[index])))process.exit(1);"""
        subprocess.run(['node','--input-type=module','-e',script],cwd=Path(__file__).resolve().parents[2],input=json.dumps({'pages':[first,last,empty],'cursors':[{},cursor,{}]}),text=True,check=True)


if __name__ == '__main__':
    unittest.main()
