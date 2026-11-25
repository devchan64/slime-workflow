import unittest
from unittest.mock import Mock
from workflow.domains.hermes_agent.minimax_form_action import apply_requested_form_update, submit_requested_form, confirm_question_handoff


class MiniMaxFormActionTests(unittest.TestCase):
    def test_question_answer_cannot_submit_another_form_or_revision(self):
        session, form = 'a'*32, 'b'*32
        snapshot={'session_id':session,'form_id':form,'revision':3,'state':'editing','service':'minimax-h3-image','request':{'prompt':'집','images':[]}}
        dispatch = Mock(side_effect=lambda command, payload: snapshot if command=='hermes-minimax-form-read' else {'resident':{'state':'not_found'}} if command=='hermes-resident-status' else {'state':'unknown'})
        prompt = f'질문 작업 2026-11-25_22-30-44-0d6a944f에 대한 답변:\n대상 폼 ID: {form}\n대상 폼 버전: 3\n1. 접수할까요?\n답변: 대기열에 접수해줘'
        payload = {'form_id':form,'revision':3}
        self.assertEqual(submit_requested_form(session,prompt,payload,dispatch)['state'],'unknown')
        for changed in ({'form_id':'c'*32,'revision':3},{'form_id':form,'revision':4}):
            with self.assertRaises(ValueError): submit_requested_form(session,prompt,changed,dispatch)
        with self.assertRaises(ValueError): submit_requested_form(session,prompt+'\n대상 폼 버전: 잘못됨',payload,dispatch)
        for answer in ('거절','접수하지 마세요'):
            rejected = prompt.replace('1. 접수할까요?\n답변: 대기열에 접수해줘', f'1. 대기열에 접수해 주세요.\n답변: {answer}')
            with self.assertRaises(ValueError): submit_requested_form(session,rejected,payload,dispatch)
        with self.assertRaises(ValueError):
            submit_requested_form(session,prompt+'\n답변 계속: 취소',payload,dispatch)
        self.assertEqual(dispatch.call_count,3)

    def test_bound_approval_respects_resident_gpu_handoff(self):
        session,form='a'*32,'b'*32
        prompt=f'질문 작업 2026-11-25_22-30-44-0d6a944f에 대한 답변:\n대상 폼 ID: {form}\n대상 폼 버전: 3\n1. 생성할까요?\n답변: 승인'
        payload={'form_id':form,'revision':3}
        snapshot={'session_id':session,'form_id':form,'revision':3,'state':'editing','service':'minimax-h3-image',
                  'source_job_id':'2026-11-25_22-30-44-0d6a944f','request':{'prompt':'집','images':[]}}
        def preview(command,payload):
            if command=='hermes-resident-status':return {'resident':{'state':'ready'},'resident_id':'resident_123'}
            if command=='hermes-minimax-form-read':return snapshot
            if command=='hermes-gpu-handoff-preview':return {'review_hash':'d'*64}
            raise AssertionError(command)
        ready=Mock(side_effect=preview)
        self.assertEqual(submit_requested_form(session,prompt,payload,ready),
                         {'state':'requires_gpu_handoff','form_id':form,'revision':3,'resident_id':'resident_123','review_hash':'d'*64})
        self.assertEqual([call.args[0] for call in ready.call_args_list],['hermes-minimax-form-read','hermes-resident-status','hermes-gpu-handoff-preview'])
        absent=Mock(side_effect=lambda command, payload: snapshot if command=='hermes-minimax-form-read' else {'resident':{'state':'not_found'}} if command=='hermes-resident-status' else {'state':'unknown'})
        self.assertEqual(submit_requested_form(session,prompt,payload,absent)['state'],'unknown')
        self.assertEqual(absent.call_args_list[2].args,('hermes-minimax-form-submit',{'session_id':session,**payload}))
        for changed in ({'form_id':form,'revision':4},{'form_id':'c'*32,'revision':3}):
            with self.assertRaises(ValueError): submit_requested_form(session,prompt,changed,absent)
        snapshot['request']={'prompt':'참조 이미지와 동일한 캐릭터','images':[]}
        with self.assertRaisesRegex(ValueError,'참조 PNG'):
            submit_requested_form(session,prompt,payload,absent)

    def test_handoff_requires_fresh_bound_snapshot_and_separate_consent(self):
        session,form='a'*32,'b'*32;job='2026-11-25_22-30-44-0d6a944f';review='d'*64;resident='resident_123'
        payload={'form_id':form,'revision':3,'resident_id':resident,'review_hash':review}
        prompt=(f'질문 작업 {job}에 대한 답변:\n대상 폼 ID: {form}\n대상 폼 버전: 3\n'
                f'상주 모델 ID: {resident}\nGPU 양도 검토: {review}\n1. GPU 양도를 진행할까요?\n답변: GPU 양도에 동의')
        snapshot={'session_id':session,'form_id':form,'revision':3,'state':'editing','service':'minimax-h3-image','source_job_id':job,'request':{'prompt':'집','images':[]}}
        def gateway(command,value):
            if command=='hermes-minimax-form-read':return snapshot
            if command=='hermes-resident-status':return {'resident_id':resident,'resident':{'state':'ready'}}
            if command=='hermes-gpu-handoff-approve':return {'id':value['request_id'],'state':'approved','revision':1}
            raise AssertionError(command)
        dispatch=Mock(side_effect=gateway)
        self.assertEqual(confirm_question_handoff(session,prompt,payload,dispatch)['state'],'approved')
        approved=dispatch.call_args_list[-1].args[1]
        self.assertTrue(approved['confirmed']);self.assertEqual(approved['review_hash'],review)
        self.assertEqual(approved['request'],{'form_id':form,'revision':3,'request':snapshot['request']})
        before=dispatch.call_count
        for text in (prompt.replace('답변: GPU 양도에 동의','답변: 거절'),prompt+'\n취소',prompt.replace(review,'e'*64)):
            with self.assertRaises(ValueError):confirm_question_handoff(session,text,payload,dispatch)
        self.assertEqual(dispatch.call_count,before)
        snapshot['revision']=4
        with self.assertRaises(ValueError):confirm_question_handoff(session,prompt,payload,dispatch)
        self.assertEqual(dispatch.call_count,before+1)

    def test_submit_requires_explicit_current_turn_and_preserves_unknown(self):
        session, form = 'a'*32, 'b'*32
        payload = {'form_id':form,'revision':3}
        dispatch = Mock(return_value={'state':'unknown','duplicate':True})
        self.assertEqual(submit_requested_form(session, '이 폼을 대기열에 접수해줘', payload, dispatch)['state'],'unknown')
        self.assertEqual(dispatch.call_args.args[0],'hermes-minimax-form-submit')
        for text in ('대기열에 접수하지 마세요', '대기열에 넣지 마세요', '대기열에 추가할 수 있나요?', '접수할 수 있나요?', '결과 보여줘', 'do not submit'):
            with self.assertRaises(ValueError): submit_requested_form(session,text,payload,dispatch)
        with self.assertRaises(ValueError): submit_requested_form(session,'대기열에 접수해줘',{**payload,'session_id':'c'*32},dispatch)
        self.assertEqual(dispatch.call_count,1)

    def test_current_user_authorizes_only_session_bound_update(self):
        session, form = 'a'*32, 'b'*32
        dispatch = Mock(return_value={'form_id':form, 'revision':2, 'state':'editing'})
        payload = {'form_id':form, 'revision':1, 'request':{'prompt':'성당'}}
        result = apply_requested_form_update(session, '폼의 프롬프트를 성당으로 바꿔줘', payload, dispatch)
        self.assertEqual(result['revision'], 2)
        self.assertEqual(dispatch.call_args.args[1]['session_id'], session)
        for prompt in ('그림을 보여줘', '폼을 수정하지 마세요', '폼을 수정할 수 있나요?', 'do not change this'):
            with self.assertRaises(ValueError): apply_requested_form_update(session, prompt, payload, dispatch)
        with self.assertRaises(ValueError):
            apply_requested_form_update(session, '폼을 수정해줘', {**payload, 'session_id':'c'*32}, dispatch)
        with self.assertRaises(ValueError):
            apply_requested_form_update(session, '해상도를 512×512로 바꿔줘', payload, dispatch)
        with self.assertRaises(ValueError):
            apply_requested_form_update(session, '시드를 1로 바꿔줘', {**payload, 'request':{'seed':1,'prompt':'다른 내용'}}, dispatch)
        with self.assertRaises(ValueError):
            apply_requested_form_update(session, '시드를 1로 바꿔줘', {**payload, 'request':{'seed':999}}, dispatch)
        with self.assertRaises(ValueError):
            apply_requested_form_update(session, '해상도를 512×512로 바꿔줘', {**payload, 'request':{'width':512,'height':1024}}, dispatch)
        with self.assertRaises(ValueError):
            apply_requested_form_update(session, '시드를 512, 해상도를 1024×1024로 바꿔줘', {**payload, 'request':{'seed':1024,'width':512,'height':1024}}, dispatch)
        self.assertEqual(dispatch.call_count, 1)

    def test_content_edit_does_not_require_prompt_keyword(self):
        session, form = 'a'*32, 'b'*32
        dispatch = Mock(return_value={'form_id':form, 'revision':2, 'state':'editing'})
        payload = {'form_id':form, 'revision':1, 'request':{'prompt':'파란 지붕 성당'}}
        apply_requested_form_update(session, '지붕을 파란색으로 바꿔줘', payload, dispatch)
        self.assertEqual(dispatch.call_count, 1)
        with self.assertRaises(ValueError):
            apply_requested_form_update(session, '해상도를 512×512로 바꿔줘', payload, dispatch)
        self.assertEqual(dispatch.call_count, 1)

    def test_explicit_numeric_values_allow_combined_edit(self):
        session, form = 'a'*32, 'b'*32
        dispatch = Mock(return_value={'form_id':form, 'revision':2, 'state':'editing'})
        payload = {'form_id':form, 'revision':1, 'request':{'seed':512,'width':1024,'height':1024}}
        result = apply_requested_form_update(session, '시드를 512, 해상도를 1024×1024로 바꿔줘', payload, dispatch)
        self.assertEqual(result['revision'],2)
        self.assertEqual(dispatch.call_args.args[1]['request'],payload['request'])


if __name__ == '__main__':
    unittest.main()
