"""표정 목록 서버와 GUI 페이지 검증의 연결을 확인한다."""
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from workflow.domains.hermes_agent.expression_observer import read_hermes_expression_catalog


class ExpressionCatalogUiContractTests(unittest.TestCase):
    def test_observed_first_last_and_empty_pages(self):
        records=[{'id':f'expression_{index}','label_ko':f'표정 {index}'} for index in range(21)]
        with patch('workflow.domains.image.expression_generation.load_expression_configuration',return_value={'expressions':records}):
            first=read_hermes_expression_catalog({'query':'','limit':20})
            cursor={'offset':20,'snapshot':first['snapshot']}
            last=read_hermes_expression_catalog({'query':'','limit':20,**cursor})
            empty=read_hermes_expression_catalog({'query':'없는 표정','limit':20})
        script="""import {validExpressionCatalogPage as valid} from './gui/expressionCatalogPage.mjs';
          let data='';for await(const part of process.stdin)data+=part;const {pages,cursors}=JSON.parse(data);
          if(!pages.every((page,index)=>valid(page,cursors[index])))process.exit(1);"""
        root=Path(__file__).resolve().parents[2]
        subprocess.run(['node','--input-type=module','-e',script],cwd=root,input=json.dumps({'pages':[first,last,empty],'cursors':[{},cursor,{}]}),text=True,check=True)


if __name__ == '__main__':
    unittest.main()
