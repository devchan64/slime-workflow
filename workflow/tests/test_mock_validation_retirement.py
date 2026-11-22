import asyncio
import json
import tempfile
import unittest
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

from workflow.common.management_asgi import build_management_application
from workflow.common.management_catalog import load_manager_page_records


class MockValidationRetirementTests(unittest.TestCase):
    def test_retired_menu_and_real_dwpose_remain_separate(self):
        names=('mock-progress-validation','mock-dwpose-validation','mock-animate-validation')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'menu.json'
            path.write_text(json.dumps({'pages':[{'id':name,'label':name,'path':'/old','category':'model-management','description':'old'} for name in names]}))
            ids={row['id'] for row in load_manager_page_records(path)}
        self.assertTrue(set(names).isdisjoint(ids))
        self.assertIn('dwpose-generator',ids)

    def test_old_routes_return_gone_without_legacy_dispatch(self):
        paths=['/management/assistant/mock-jobs']
        paths += ['/management/frame/'+name+suffix for name in ('mock-progress-validation','mock-dwpose-validation','mock-animate-validation') for suffix in ('','/')]
        with tempfile.TemporaryDirectory() as directory, patch('workflow.common.management_asgi.execute_legacy_request') as legacy:
            root=Path(directory)
            app=build_management_application(SimpleHTTPRequestHandler,root,root/'missing.json',8770,[])
            async def check():
                for path in paths:
                    for method in (('GET','POST') if path.endswith('mock-jobs') else ('GET',)):
                        messages=[]
                        async def receive(): return {'type':'http.request','body':b'','more_body':False}
                        async def send(message): messages.append(message)
                        await app({'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':method,'scheme':'http','path':path,'raw_path':path.encode(),'query_string':b'','root_path':'','headers':[],'server':('localhost',8770),'client':('127.0.0.1',1000)},receive,send)
                        self.assertEqual(messages[0]['status'],410,(path,method))
            asyncio.run(check())
            legacy.assert_not_called()
