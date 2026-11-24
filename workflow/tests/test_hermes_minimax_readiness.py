import unittest
from unittest.mock import patch
from workflow.domains.hermes_agent.management_observer import read_hermes_model_readiness

class MiniMaxReadinessTest(unittest.TestCase):
    def test_read_only_model_status_and_disabled_gateway(self):
        for service in ('minimax-h3-image','minimax-h3-i2v'):
            with self.subTest(service=service), patch('workflow.common.management_gateway.execute_management_command',return_value={'ready':True,'generation_ready':True,'missing':['private/path']}) as call:
                result=read_hermes_model_readiness(service)
                self.assertEqual(result['status'],'available');self.assertTrue(result['generation_ready']);self.assertNotIn('missing',result)
                self.assertEqual(call.call_args.args[:3],(service,'model-status',{}))
            with patch('workflow.common.management_gateway.execute_management_command',side_effect=ValueError('disabled')):
                self.assertEqual(read_hermes_model_readiness(service)['status'],'unavailable')
        with self.assertRaises(ValueError):read_hermes_model_readiness('unknown-service')

    def test_sandbox_bridge_queries_minimax_readiness(self):
        import json,socket,threading
        from workflow.domains.hermes_agent.management_bridge import handle_hermes_observer_connection
        client,server=socket.socketpair()
        with client, patch('workflow.common.management_gateway.execute_management_command',return_value={'ready':True,'generation_ready':True}):
            thread=threading.Thread(target=handle_hermes_observer_connection,args=(server,));thread.start()
            client.sendall(b'model-readiness minimax-h3-image\n')
            response=json.loads(client.makefile('rb').readline());thread.join(timeout=3)
        self.assertFalse(thread.is_alive());self.assertEqual(response['service'],'minimax-h3-image');self.assertTrue(response['generation_ready'])
