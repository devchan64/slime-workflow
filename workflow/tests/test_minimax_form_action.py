import unittest
from unittest.mock import Mock
from workflow.domains.hermes_agent.minimax_form_action import apply_requested_form_update, submit_requested_form


class MiniMaxFormActionTests(unittest.TestCase):
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
