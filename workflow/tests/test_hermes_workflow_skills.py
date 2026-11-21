import unittest
from pathlib import Path

from workflow.domains.hermes_agent.workflow_skills import build_workflow_guidance, select_workflow_skills


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


if __name__ == '__main__':
    unittest.main()
