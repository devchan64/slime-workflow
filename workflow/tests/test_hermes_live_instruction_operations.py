import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest

from workflow.domains.hermes_agent.live_instruction_operations import deliver, settle
from workflow.domains.hermes_agent.session_store import HermesSessionStore


class Manager:
    def __init__(self, root): self.root = root
    def resolve_hermes_job_path(self, job_id): return self.root / job_id


class LiveInstructionOperationsTests(unittest.TestCase):
    def test_delivery_idempotence_and_settlement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = HermesSessionStore(root / 'sessions')
            session, job = 'a' * 32, '2026-11-22_00-05-05-d6a85e1b'
            store.create_session_record(session)
            store.append_session_request(session, 'request_prev', '질문')
            store.attach_session_job(session, 'request_prev', job)
            directory = root / job
            (directory / 'live-control').mkdir(parents=True)
            (directory / 'status.json').write_text('{"status":"running"}')
            server = socket.socket(socket.AF_UNIX)
            server.bind(str(directory / 'live-control' / 'agent.sock'))
            server.listen(1)
            received = []
            def worker():
                with server.accept()[0] as connection:
                    request = json.loads(connection.recv(20000))
                    received.append(request)
                    connection.sendall(json.dumps({'request_id':request['request_id'],'state':'accepted'}).encode()+b'\n')
            thread = threading.Thread(target=worker)
            thread.start()
            manager = Manager(root)
            payload = {'session_id':session,'job_id':job,'request_id':'request_live','mode':'steer','text':'추가'}
            self.assertEqual(deliver(manager,store,payload)['state'], 'accepted')
            thread.join(2)
            server.close()
            self.assertEqual(deliver(manager,store,payload)['state'], 'accepted')
            self.assertEqual(len(received), 1)
            (directory / 'live-control' / 'settled.json').write_text(json.dumps([{'request_id':'request_live','state':'applied'}]))
            rows=store.read_session_record(session)['live_instructions']
            self.assertEqual(settle(manager,store,session,rows)[0]['state'], 'applied')

    def test_connection_lost_is_unknown_and_not_replayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=HermesSessionStore(root/'sessions');session='c'*32
            job='2026-11-22_00-05-05-d6a85e1b';store.create_session_record(session)
            store.append_session_request(session,'request_prev','질문');store.attach_session_job(session,'request_prev',job)
            directory=root/job;(directory/'live-control').mkdir(parents=True);(directory/'status.json').write_text('{"status":"running"}')
            server=socket.socket(socket.AF_UNIX);server.bind(str(directory/'live-control'/'agent.sock'));server.listen(1)
            def disconnect():
                with server.accept()[0] as connection: connection.recv(20000)
            thread=threading.Thread(target=disconnect);thread.start()
            payload={'session_id':session,'job_id':job,'request_id':'request_live','mode':'redirect','text':'수정'}
            self.assertEqual(deliver(Manager(root),store,payload)['state'],'unknown')
            thread.join(2);server.close()
            self.assertEqual(deliver(Manager(root),store,payload)['state'],'unknown')
            (directory/'live-control'/'settled.json').write_text(json.dumps([{'request_id':'request_live','state':'applied'}]))
            rows=store.read_session_record(session)['live_instructions']
            self.assertEqual(settle(Manager(root),store,session,rows)[0]['state'],'applied')

    def test_service_recovery_is_idempotent_and_rejects_unknown(self):
        from workflow.domains.hermes_agent.service import HermesServiceManager
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=HermesSessionStore(root/'sessions');session='d'*32
            job='2026-11-22_00-05-05-d6a85e1b';store.create_session_record(session)
            store.append_session_request(session,'request_prev','질문');store.attach_session_job(session,'request_prev',job)
            job_root=root/'jobs'/job;job_root.mkdir(parents=True);(job_root/'status.json').write_text('{"status":"running"}')
            manager=HermesServiceManager(root/'jobs',root/'sessions')
            payload={'session_id':session,'job_id':job,'request_id':'request_live','mode':'steer','text':'추가'}
            self.assertEqual(manager.execute_hermes_command('hermes-live-instruction',payload)['state'],'undelivered')
            request={'session_id':session,'request_id':'request_live'}
            self.assertFalse(manager.execute_hermes_command('hermes-live-instruction-recover',request)['duplicate'])
            self.assertTrue(manager.execute_hermes_command('hermes-live-instruction-recover',request)['duplicate'])
            self.assertEqual(len(store.read_session_record(session)['chat_queue']),1)

    def test_recovery_display_tracks_queued_dispatched_and_cancelled(self):
        from workflow.domains.hermes_agent.live_instruction_operations import annotate_recoveries, recovery_id
        row = {'request_id': 'request_live', 'state': 'undelivered'}
        self.assertNotIn('recovery', annotate_recoveries([dict(row)], {'chat_queue': [], 'messages': []})[0])
        for state in ('queued', 'dispatching', 'dispatched', 'cancelled'):
            entry = {'request_id': recovery_id('request_live'), 'state': state, 'job_id': 'job_12345'}
            result = annotate_recoveries([dict(row)], {'chat_queue': [entry], 'messages': []})[0]
            self.assertEqual(result['recovery'], {'state': state, 'job_id': 'job_12345'})
        message = {'request_id': recovery_id('request_live'), 'job_id': 'job_12345'}
        result = annotate_recoveries([dict(row)], {'chat_queue': [], 'messages': [message]})[0]
        self.assertEqual(result['recovery'], {'state': 'dispatched', 'job_id': 'job_12345'})

    def test_missing_endpoint_is_recoverable_undelivered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=HermesSessionStore(root/'sessions');session='b'*32
            job='2026-11-22_00-05-05-d6a85e1b';store.create_session_record(session)
            store.append_session_request(session,'request_prev','질문');store.attach_session_job(session,'request_prev',job)
            (root/job).mkdir();(root/job/'status.json').write_text('{"status":"running"}')
            row=deliver(Manager(root),store,{'session_id':session,'job_id':job,'request_id':'request_live','mode':'redirect','text':'수정'})
            self.assertEqual(row['state'],'undelivered')
