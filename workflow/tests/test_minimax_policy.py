"""MiniMax 우선 선택 옵션과 게이트웨이 상태 계약."""
import io
import json
import unittest
from unittest.mock import Mock, patch
from gateway.server import parse_gateway_arguments
from workflow.common.minimax_policy import read_minimax_preference
from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_video_proposal


class MiniMaxPolicyTests(unittest.TestCase):
    def test_gateway_option_is_opt_in(self):
        self.assertFalse(parse_gateway_arguments([]).minimax)
        self.assertTrue(parse_gateway_arguments(['--minimax']).minimax)

    def test_policy_reads_gateway_and_distinguishes_failure(self):
        response = io.BytesIO(json.dumps({'role': 'management-gateway', 'minimax_preferred': True}).encode())
        opener = Mock()
        opener.open.return_value = response
        with patch('workflow.common.minimax_policy.build_opener', return_value=opener):
            self.assertIs(read_minimax_preference(), True)
        opener.open.side_effect = OSError('offline')
        with patch('workflow.common.minimax_policy.build_opener', return_value=opener):
            self.assertIsNone(read_minimax_preference())

    def test_minimax_video_proposal(self):
        answer = 'HERMES_VIDEO_PROPOSAL\n{"service":"minimax-h3-i2v","mode":"first_frame","prompt":"walk"}\nEND_HERMES_VIDEO_PROPOSAL'
        self.assertEqual(parse_hermes_video_proposal(answer)['service'], 'minimax-h3-i2v')

class MiniMaxSelectionTests(unittest.TestCase):
    def setUp(self):
        priority_patch = patch('workflow.common.generator_availability.preferred_ready', return_value=None)
        priority_patch.start()
        self.addCleanup(priority_patch.stop)

    def test_selection_respects_policy_and_explicit_choice(self):
        from workflow.domains.hermes_agent.video_selection import select_video_proposal
        proposal = {'service':'wan22-i2v', 'mode':'first_frame', 'prompt':'walk', 'explicit_service':False}
        request = {'prompt':'첫 이미지로 걷는 영상을 만들어 줘', 'minimax_preferred':True}
        self.assertEqual(select_video_proposal(proposal, request)['service'], 'minimax-h3-i2v')
        self.assertEqual(select_video_proposal(proposal, {**request, 'minimax_preferred':False})['service'], 'wan22-i2v')
        self.assertEqual(select_video_proposal({**proposal, 'explicit_service':True}, {**request, 'prompt':'wan22-i2v로 만들어 줘'})['service'], 'wan22-i2v')
        with self.assertRaises(ValueError):
            select_video_proposal(proposal, {**request, 'prompt':'wan22-i2v로 만들어 줘'})
        with self.assertRaises(ValueError):
            select_video_proposal({key:value for key,value in proposal.items() if key!='explicit_service'}, request)
        with self.assertRaises(ValueError):
            select_video_proposal(proposal, {**request, 'prompt':'Wan 2.2로 만들어 줘'})
        text_proposal = {'service':'wan22-vace', 'mode':'text', 'prompt':'walk', 'explicit_service':False}
        self.assertEqual(select_video_proposal(text_proposal, request)['service'], 'wan22-vace')
        self.assertEqual(select_video_proposal({'service':'wan22-i2v','mode':'first_frame','prompt':'x'}, {'prompt':'legacy'}), {'service':'wan22-i2v','mode':'first_frame','prompt':'x'})
