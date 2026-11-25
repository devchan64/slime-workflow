import json
import unittest
from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_flux_proposal

from workflow.domains.hermes_agent.image_selection import select_image_proposal


class ImageSelectionTests(unittest.TestCase):
    def test_validation_uses_selected_generator(self):
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_image_proposal
        proposal = {'prompt':'가'*6100, 'width':512, 'height':512, 'seed':42, 'explicit_service':False}
        answer = 'HERMES_IMAGE_PROPOSAL\n'+json.dumps(proposal, ensure_ascii=False)+'\nEND_HERMES_IMAGE_PROPOSAL'
        parsed = parse_hermes_image_proposal(answer)
        request = {'image_selection_version':1, 'minimax_preferred':True, 'prompt':'이미지 생성'}
        self.assertEqual(select_image_proposal(parsed, request)['service'], 'minimax-h3-image')
        with self.assertRaises(ValueError):
            select_image_proposal(parsed, {**request, 'minimax_preferred':False})

    def test_image_marker_keeps_legacy_compatibility(self):
        from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_image_proposal
        value = {'prompt':'blue sky', 'width':512, 'height':512, 'seed':42}
        def answer(marker): return marker+'\n'+json.dumps(value)+'\nEND_'+marker
        self.assertEqual(parse_hermes_image_proposal(answer('HERMES_IMAGE_PROPOSAL')), value)
        self.assertEqual(parse_hermes_image_proposal(answer('HERMES_FLUX_PROPOSAL')), value)
        with self.assertRaises(ValueError):
            parse_hermes_image_proposal(answer('HERMES_IMAGE_PROPOSAL')+'\n'+answer('HERMES_FLUX_PROPOSAL'))

    def setUp(self):
        self.proposal = {'service':'flux-image','prompt':'a house','width':1024,'height':1024,'seed':42,'explicit_service':False}
        self.request = {'image_selection_version':1,'minimax_preferred':True,'prompt':'집 이미지 만들어줘'}

    def test_policy_and_explicit_choice(self):
        self.assertEqual(select_image_proposal(self.proposal,self.request)['service'],'minimax-h3-image')
        self.assertEqual(select_image_proposal(self.proposal,{**self.request,'minimax_preferred':False})['service'],'flux-image')
        explicit = {**self.proposal,'explicit_service':True}
        self.assertEqual(select_image_proposal(explicit,{**self.request,'prompt':'FLUX로 집 이미지'})['service'],'flux-image')
        self.assertEqual(select_image_proposal(explicit,{**self.request,'prompt':'미니맥스로 집 이미지'})['service'],'minimax-h3-image')
        with self.assertRaises(ValueError): select_image_proposal(self.proposal,{**self.request,'prompt':'FLUX로 집 이미지'})
        with self.assertRaises(ValueError): select_image_proposal({**self.proposal,'width':512,'explicit_service':True},{**self.request,'prompt':'미니맥스로 집'})

    def test_unsupported_and_old_records_keep_flux(self):
        small = {**self.proposal,'width':512,'height':512}
        self.assertEqual(select_image_proposal(small,self.request)['service'],'minimax-h3-image')
        self.assertEqual(select_image_proposal({**small,'explicit_service':True},{**self.request,'prompt':'미니맥스로 집'})['service'],'minimax-h3-image')
        old = {key:value for key,value in self.proposal.items() if key!='explicit_service'}
        self.assertEqual(select_image_proposal(old,{'minimax_preferred':True}),old)
        with self.assertRaises(ValueError): select_image_proposal(old,self.request)

    def test_parser_validates_optional_explicit_flag(self):
        def parse(value): return parse_hermes_flux_proposal('HERMES_FLUX_PROPOSAL\n'+json.dumps(value)+'\nEND_HERMES_FLUX_PROPOSAL')
        self.assertEqual(parse(self.proposal),self.proposal)
        with self.assertRaises(ValueError): parse({**self.proposal,'explicit_service':'yes'})
