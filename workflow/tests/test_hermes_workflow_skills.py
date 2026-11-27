import unittest
import json
import shutil
import tempfile
from pathlib import Path

from workflow.domains.hermes_agent.workflow_skills import build_workflow_guidance, select_workflow_skills, load_skill_registry, SKILL_ROOT


class WorkflowSkillTests(unittest.TestCase):
    def test_short_form_submission_selects_generation_skill(self):
        for prompt in ('이 폼을 접수해줘', '대기열에 넣어줘', '시드를 42로 변경해줘'):
            with self.subTest(prompt=prompt):
                self.assertIn('generation-request',select_workflow_skills(prompt))

    def test_natural_form_edit_selects_generation_skill(self):
        self.assertIn('generation-request', select_workflow_skills('지붕을 파란색으로 바꿔줘'))
        self.assertIn('generation-request', select_workflow_skills('대기열에 추가해줘'))
    def test_building_anchor_guidance_requires_observation_and_confirmation(self):
        root=Path(__file__).resolve().parents[2]
        guidance=build_workflow_guidance(root,'건물 앵커를 변경해줘')
        self.assertIn('[워크플로우 스킬: map-asset-review]',guidance)
        self.assertIn('HERMES_BUILDING_PROPOSAL',guidance)
        self.assertIn('저장을 명시적으로 확인',guidance)
        self.assertIn('자동 재저장하지 않는다',guidance)

    def test_gpu_memory_requests_include_handoff_guidance(self):
        root = Path(__file__).resolve().parents[2]
        for prompt in ('GPU 메모리를 확보해줘', 'VRAM이 부족해', '상주 모델을 내려줘'):
            with self.subTest(prompt=prompt):
                guidance = build_workflow_guidance(root, prompt)
                self.assertIn('[워크플로우 스킬: generation-request]', guidance)
                self.assertIn('GPU 자원 관리는 스케줄러의 역할', guidance)
                self.assertIn('다른 프로세스를 종료하지 않는다', guidance)
                self.assertIn('재적재를 보장하지 않는다', guidance)

    def test_selection_and_combinations(self):
        self.assertEqual(select_workflow_skills('안녕하세요'), [])
        self.assertEqual(select_workflow_skills('기존 영상 결과 조회'), ['generation-result-lookup', 'generation-request'])
        self.assertEqual(select_workflow_skills('스프라이트 좌표 수정'), ['generator-development', 'map-asset-review'])
        self.assertNotIn('map-asset-review', select_workflow_skills('mapping'))

    def test_followup_uses_user_context_not_assistant_content(self):
        context = {'messages': [{'role': 'user', 'content': 'Kimodo 작업 결과'}, {'role': 'assistant', 'content': '스프라이트 수정'}]}
        selected = select_workflow_skills('그것을 확인해줘', context)
        self.assertIn('generation-result-lookup', selected)
        self.assertIn('history-operations', selected)
        self.assertNotIn('map-asset-review', selected)

    def test_flux_conversation_carries_generation_and_result_guidance(self):
        root = Path(__file__).resolve().parents[2]
        context = {'messages': [{'role': 'user', 'content': 'FLUX 캐릭터 이미지를 생성해줘'}]}
        selected = select_workflow_skills('결과를 확인해줘', context)
        self.assertIn('generation-request', selected)
        self.assertIn('generation-result-lookup', selected)
        guidance = build_workflow_guidance(root, '결과를 확인해줘', context)
        self.assertIn('16스텝', guidance)
        self.assertIn('자동 연결되지', guidance)
        self.assertIn('flux-source-status', guidance)
        self.assertIn('작업 ID가 생기기 전', guidance)
        self.assertIn('자동 재접수하지 않는다', guidance)

    def test_show_it_followup_selects_result_lookup_only_with_media_context(self):
        context={'messages':[{'role':'user','content':'FLUX 캐릭터 이미지를 생성해줘'}]}
        self.assertIn('generation-result-lookup',select_workflow_skills('그거 보여줘',context))
        self.assertNotIn('generation-result-lookup',select_workflow_skills('그거 보여줘',{'messages':[{'role':'user','content':'코드를 수정해줘'}]}))
        self.assertNotIn('generation-result-lookup',select_workflow_skills('그거 보여줘',{'messages':[{'role':'assistant','content':'이미지 생성 완료'}]}))
        self.assertIn('generation-result-lookup',select_workflow_skills('이미지 보여줘'))
        unrelated={'messages':[{'role':'user','content':'FLUX 이미지를 생성해줘'}, {'role':'user','content':'이제 코드 설명해줘'}]}
        self.assertNotIn('generation-result-lookup',select_workflow_skills('그거 보여줘',unrelated))

    def test_followup_never_selects_unregistered_skill(self):
        source=Path(__file__).resolve().parents[2] / SKILL_ROOT
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory); root=workspace/SKILL_ROOT; shutil.copytree(source,root)
            path=root/'registry.json'; registry=json.loads(path.read_text())
            registry['skills']=[row for row in registry['skills'] if row['name']!='generation-result-lookup']
            path.write_text(json.dumps(registry,ensure_ascii=False))
            context={'messages':[{'role':'user','content':'FLUX 이미지를 생성해줘'}]}
            self.assertNotIn('generation-result-lookup',select_workflow_skills('그거 보여줘',context,workspace))
            self.assertNotIn('[워크플로우 스킬: generation-result-lookup]',build_workflow_guidance(workspace,'그거 보여줘',context))

    def test_guidance_reads_only_selected_snapshot_files(self):
        root = Path(__file__).resolve().parents[2]
        guidance = build_workflow_guidance(root, '기존 작업 이력 조회')
        self.assertIn('[워크플로우 공통 입문]', guidance)
        self.assertIn('[워크플로우 스킬: history-operations]', guidance)
        self.assertNotIn('[워크플로우 스킬: map-asset-review]', guidance)
        self.assertNotIn('[워크플로우 스킬: generation-result-lookup]', guidance)

    def test_snapshot_registry_controls_selection_and_rejects_invalid_entries(self):
        source = Path(__file__).resolve().parents[2] / SKILL_ROOT
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / SKILL_ROOT
            shutil.copytree(source, root)
            registry_path = root / 'registry.json'
            registry = json.loads(registry_path.read_text())
            result_skill = next(item for item in registry['skills'] if item['name'] == 'generation-result-lookup')
            result_skill['terms'].append('새단어')
            registry_path.write_text(json.dumps(registry, ensure_ascii=False))
            self.assertEqual(select_workflow_skills('새단어', workspace=workspace), ['generation-result-lookup'])
            self.assertEqual(select_workflow_skills('새단어'), [])
            result_skill['name'] = '../outside'
            registry_path.write_text(json.dumps(registry))
            with self.assertRaises(ValueError):
                load_skill_registry(workspace)

    def test_duplicate_registration_and_symlink_are_rejected(self):
        source = Path(__file__).resolve().parents[2] / SKILL_ROOT
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / SKILL_ROOT
            shutil.copytree(source, root)
            registry_path = root / 'registry.json'
            registry = json.loads(registry_path.read_text())
            registry['skills'].append(registry['skills'][0])
            registry_path.write_text(json.dumps(registry))
            with self.assertRaises(ValueError):
                load_skill_registry(workspace)
            registry['skills'].pop()
            registry_path.write_text(json.dumps(registry))
            skill = root / registry['skills'][0]['name'] / 'SKILL.md'
            skill.unlink()
            skill.symlink_to(source / registry['skills'][0]['name'] / 'SKILL.md')
            with self.assertRaises(ValueError):
                load_skill_registry(workspace)


if __name__ == '__main__':
    unittest.main()
