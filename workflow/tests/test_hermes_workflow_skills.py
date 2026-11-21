import unittest
import json
import shutil
import tempfile
from pathlib import Path

from workflow.domains.hermes_agent.workflow_skills import build_workflow_guidance, select_workflow_skills, load_skill_registry, SKILL_ROOT


class WorkflowSkillTests(unittest.TestCase):
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
            registry['skills'][0]['terms'].append('새단어')
            registry_path.write_text(json.dumps(registry, ensure_ascii=False))
            self.assertEqual(select_workflow_skills('새단어', workspace=workspace), ['generation-result-lookup'])
            self.assertEqual(select_workflow_skills('새단어'), [])
            registry['skills'][0]['name'] = '../outside'
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
