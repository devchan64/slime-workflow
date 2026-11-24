import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from workflow.domains.hermes_agent.minimax_report_evidence import inspect_minimax_result


def save(path, value):
    path.write_text(json.dumps(value))


class MiniMaxEvidenceTests(unittest.TestCase):
    def test_image_recorded_settings_disagreement_is_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            save(root/'status.json',{'status':'completed'})
            save(root/'request.json',{'prompt':'house','width':16,'height':16,'steps':6,'seed':42})
            Image.new('RGB',(16,16)).save(root/'result.png')
            save(root/'result.json',{'image_sha256':hashlib.sha256((root/'result.png').read_bytes()).hexdigest(),
                                     'width':16,'height':16,'steps':6,'seed':43})
            result=inspect_minimax_result(root,'minimax-h3-image')
            self.assertEqual(result['checks']['recorded_settings_match'],'fail')
            self.assertIn('독립적인',result['recorded_settings_note'])

    def test_image_result_and_missing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            save(root/'status.json', {'status':'completed'})
            save(root/'request.json', {'prompt':'house', 'width':16, 'height':16})
            Image.new('RGB',(16,16)).save(root/'result.png')
            save(root/'result.json',{'image_sha256':hashlib.sha256((root/'result.png').read_bytes()).hexdigest()})
            result = inspect_minimax_result(root,'minimax-h3-image')
            self.assertEqual(result['image']['dimensions'],[16,16])
            (root/'result.png').unlink()
            with self.assertRaises(ValueError): inspect_minimax_result(root,'minimax-h3-image')

    def test_video_samples_match_current_completed_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); attempt='a'*32; directory=root/'attempts'/attempt; directory.mkdir(parents=True)
            save(root/'status.json',{'status':'completed','attempt':attempt})
            save(root/'current-attempt.json',{'id':attempt})
            Image.new('RGB',(8,8)).save(root/'reference-1.png')
            reference = (root/'reference-1.png').read_bytes()
            save(root/'request.json',{'prompt':'move','references':['reference-1.png'],'reference_snapshots':[{'path':'reference-1.png','sha256':hashlib.sha256(reference).hexdigest(),'bytes':len(reference),'order':1}]})
            hashes=[]
            for i in range(3):
                path=directory/f'output-{i:03d}.png'; Image.new('RGB',(8,8),(i,0,0)).save(path); hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
            (directory/'preview.mp4').write_bytes(b'video')
            save(directory/'result.json',{'frames':3,'fps':24,'output_sha256':hashes,'video_sha256':hashlib.sha256(b'video').hexdigest()})
            result=inspect_minimax_result(root,'minimax-h3-i2v')
            self.assertEqual([item['frame'] for item in result['samples']],[0,1,2])
            (directory/'output-001.png').write_bytes(b'broken')
            with self.assertRaises((ValueError,OSError)): inspect_minimax_result(root,'minimax-h3-i2v')
            save(root/'status.json',{'status':'completed','attempt':'b'*32})
            with self.assertRaises(ValueError): inspect_minimax_result(root,'minimax-h3-i2v')

    def test_visual_observation_checks_hash_and_reports_failure(self):
        from types import SimpleNamespace
        from workflow.domains.hermes_agent.minimax_report_evidence import observe_minimax_result
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            save(root/'status.json',{'status':'completed'})
            save(root/'request.json',{'prompt':'house'})
            Image.new('RGB',(16,16)).save(root/'result.png')
            save(root/'result.json',{'image_sha256':hashlib.sha256((root/'result.png').read_bytes()).hexdigest()})
            evidence=inspect_minimax_result(root,'minimax-h3-image')
            observed_kwargs=[]
            def ok(args, **kwargs):
                observed_kwargs.append(kwargs)
                return SimpleNamespace(stdout=json.dumps({'image_sha256':args[-1],'observation':'house'}))
            self.assertEqual(observe_minimax_result(root,evidence,runner=ok,lock_fd=123,memory_reader=lambda:11*1024*1024)[0]['observation'],'house')
            self.assertEqual(observed_kwargs[0]['pass_fds'],(123,))
            def failed(*args, **kwargs): raise OSError('unavailable')
            self.assertIn('unavailable',observe_minimax_result(root,evidence,runner=failed,memory_reader=lambda:11*1024*1024)[0])
            with self.assertRaises(RuntimeError): observe_minimax_result(root,evidence,runner=ok,memory_reader=lambda:0)
            Image.new('RGB',(16,16),'red').save(root/'result.png')
            with self.assertRaises(ValueError): observe_minimax_result(root,evidence,runner=ok,memory_reader=lambda:11*1024*1024)

    def test_video_observation_uses_decoded_mp4_samples(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from workflow.domains.hermes_agent.minimax_report_evidence import observe_minimax_result
        evidence={'service':'minimax-h3-i2v','attempt':'a'*32,'reference':{'sha256':'b'*64},'video':{'sha256':'c'*64}}
        def run(args, **kwargs):
            if any(arg.endswith('minimax_video_samples.py') for arg in args):
                path=Path(args[-1])/'sample-00000.png';Image.new('RGB',(8,8)).save(path)
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                return SimpleNamespace(stdout=json.dumps({'frames':1,'duration_seconds':1,'fps':1,'dimensions':[8,8],'samples':[{'filename':path.name,'sha256':digest,'seconds':0,'frame':0}]}))
            return SimpleNamespace(stdout=json.dumps({'image_sha256':args[-1],'observation':'frame content'}))
        with tempfile.TemporaryDirectory() as temp, patch('workflow.domains.hermes_agent.minimax_report_evidence.inspect_minimax_result',return_value=evidence):
            observations=observe_minimax_result(Path(temp),evidence,runner=run,memory_reader=lambda:11*1024*1024)
        self.assertEqual([item['source'] for item in observations],['reference','final_video'])
        self.assertEqual(observations[1]['video_frames'],1)
        self.assertEqual(observations[1]['observation'],'frame content')

    def test_video_decode_failure_is_reported_as_unavailable(self):
        import subprocess
        from types import SimpleNamespace
        from unittest.mock import patch
        from workflow.domains.hermes_agent.minimax_report_evidence import observe_minimax_result
        evidence={'service':'minimax-h3-i2v','attempt':'a'*32,'reference':{'sha256':'b'*64},'video':{'sha256':'c'*64}}
        def run(args, **kwargs):
            if any(arg.endswith('minimax_video_samples.py') for arg in args):
                raise subprocess.CalledProcessError(1,args)
            return SimpleNamespace(stdout=json.dumps({'image_sha256':args[-1],'observation':'reference'}))
        with tempfile.TemporaryDirectory() as temp, patch('workflow.domains.hermes_agent.minimax_report_evidence.inspect_minimax_result',return_value=evidence):
            values=observe_minimax_result(Path(temp),evidence,runner=run,memory_reader=lambda:11*1024*1024)
        self.assertTrue(any(item['source']=='final_video' and 'unavailable' in item for item in values))
        self.assertTrue(any(item['source']=='reference' and item.get('observation')=='reference' for item in values))
