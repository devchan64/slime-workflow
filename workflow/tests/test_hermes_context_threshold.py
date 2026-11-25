import tempfile
import unittest
from pathlib import Path
from workflow.domains.hermes_agent.session_store import HermesSessionStore
from workflow.domains.hermes_agent.context_runtime import compress_context

class ContextThresholdTests(unittest.TestCase):
    def test_session_setting_is_explicit_and_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=HermesSessionStore(Path(tmp));a='a'*32;b='b'*32
            store.create_session_record(a);store.create_session_record(b)
            store.set_context_threshold(a,16000)
            self.assertEqual(store.read_session_record(a)['context_threshold'],16000)
            self.assertNotIn('context_threshold',store.read_session_record(b))
            for invalid in (True,0,7000,64000,'16000'):
                with self.assertRaises(ValueError):store.set_context_threshold(a,invalid)
            store.set_context_threshold(a,None);self.assertNotIn('context_threshold',store.read_session_record(a))
    def test_threshold_controls_trigger_and_preserves_default(self):
        class Compressor:
            threshold_tokens=54400
            def __init__(self,**kwargs):pass
            def should_compress(self,count):return count>=self.threshold_tokens
            def _generate_summary(self,*args):return '요약'
            def compress(self,messages,current_tokens,force):
                self._generate_summary(messages)
                return [{'role':'assistant','content':'요약','_compressed_summary':True}]
        messages=[{'role':'user','content':'기존 내용'}]
        self.assertEqual(compress_context(messages,23999,'local',compressor_factory=Compressor)['state'],'not_needed')
        default=compress_context(messages,24000,'local',compressor_factory=Compressor)
        self.assertEqual((default['state'],default['threshold']),('compressed',24000))
        result=compress_context(messages,8000,'local',compressor_factory=Compressor,threshold_tokens=8000)
        self.assertEqual(result['state'],'compressed');self.assertEqual(result['threshold'],8000)
        with self.assertRaises(ValueError):compress_context(messages,20000,'local',compressor_factory=Compressor,threshold_tokens=True)

    def test_gateway_settings_and_capability_contract(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with tempfile.TemporaryDirectory() as tmp:
            manager=HermesServiceManager(Path(tmp)/'jobs',Path(tmp)/'sessions');session='a'*32
            manager.execute_hermes_command('hermes-session-create',{'session_id':session})
            self.assertEqual(manager.execute_hermes_command('hermes-session-context-settings',{'session_id':session,'threshold':32000})['threshold'],32000)
            with self.assertRaises(ValueError):manager.execute_hermes_command('hermes-session-context-settings',{'session_id':session,'threshold':16000,'enabled':True})
