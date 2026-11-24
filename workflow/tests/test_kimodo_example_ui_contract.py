"""등록된 Kimodo 예시와 GUI 응답 검증의 호환성을 확인한다."""
import json
from pathlib import Path
import subprocess
import unittest

from generators.kimodo.form_inputs import load_kimodo_examples, load_proportion_examples


class KimodoExampleUiContractTests(unittest.TestCase):
    def test_registered_reference_example_list_is_accepted(self):
        examples=[{'id':key,'label':value['label']} for key,value in load_proportion_examples().items()]
        script="""import {validKimodoReferenceExamples as valid} from './gui/kimodoReferenceExamples.mjs';let text='';for await(const chunk of process.stdin)text+=chunk;
          if(!valid(JSON.parse(text),false))process.exit(1);"""
        subprocess.run(['node','--input-type=module','-e',script],cwd=Path(__file__).resolve().parents[2],input=json.dumps(examples),text=True,check=True)

    def test_registered_examples_are_accepted(self):
        examples=[{**value,'references':[]} for value in load_kimodo_examples().values()]
        self.assertTrue(examples)
        script="""import {validKimodoExample as valid} from './gui/kimodoExampleValidation.mjs';let text='';for await(const chunk of process.stdin)text+=chunk;
          if(!JSON.parse(text).every(valid))process.exit(1);"""
        subprocess.run(['node','--input-type=module','-e',script],cwd=Path(__file__).resolve().parents[2],input=json.dumps(examples),text=True,check=True)

    def test_registered_prompt_example_list_is_accepted(self):
        examples=[{key:value[key] for key in ('id','label','prompt')} for value in load_kimodo_examples().values()]
        script="""import {validKimodoExampleList as valid} from './gui/kimodoExampleValidation.mjs';let text='';for await(const chunk of process.stdin)text+=chunk;
          if(!valid(JSON.parse(text)))process.exit(1);"""
        subprocess.run(['node','--input-type=module','-e',script],cwd=Path(__file__).resolve().parents[2],input=json.dumps(examples),text=True,check=True)


if __name__ == '__main__':
    unittest.main()
