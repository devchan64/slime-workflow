import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import threading
from unittest.mock import patch

from workflow.common.generator_availability import collect_availability, preferred_ready, read_fresh_availability, read_priorities, start_availability_scheduler, write_availability


class GeneratorAvailabilityTest(unittest.TestCase):
    def test_scheduler_refreshes_and_stops(self):
        stop = threading.Event()
        calls = []
        def record(value):
            calls.append(value)
            if len(calls) == 2:
                stop.set()
        with patch('workflow.common.generator_availability.collect_availability', return_value={'snapshot': True}), \
             patch('workflow.common.generator_availability.write_availability', side_effect=record):
            thread = start_availability_scheduler(stop, interval=0.01)
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(calls), 2)

    def test_selection_applies_priority_but_preserves_explicit_choice(self):
        from workflow.domains.hermes_agent.image_selection import select_image_proposal
        from workflow.domains.hermes_agent.video_selection import select_video_proposal
        image = {'service':'flux-image', 'prompt':'house', 'width':512, 'height':512, 'seed':42, 'explicit_service':False}
        request = {'image_selection_version':1, 'minimax_preferred':False, 'prompt':'집 그림'}
        with patch('workflow.common.generator_availability.preferred_ready', return_value='minimax-h3-image'):
            self.assertEqual(select_image_proposal(image, request)['service'], 'minimax-h3-image')
            self.assertEqual(select_image_proposal({**image,'explicit_service':True}, {**request,'prompt':'FLUX 그림'})['service'], 'flux-image')
        video = {'service':'wan22-i2v', 'mode':'first_frame', 'prompt':'walk', 'explicit_service':False}
        with patch('workflow.common.generator_availability.preferred_ready', return_value='minimax-h3-i2v'):
            self.assertEqual(select_video_proposal(video, {'minimax_preferred':False,'prompt':'영상'})['service'], 'minimax-h3-i2v')

    def test_priority_uses_fresh_ready_entries_and_ignores_unknown(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); status = root/'status.json'; priority = root/'priority.json'
            priority.write_text(json.dumps({'schema_version': 1, 'image': ['flux-image', 'minimax-h3-image'],
                                            'video_first_frame': ['minimax-h3-i2v']}))
            data = {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(),
                    'services': {'flux-image': {'state': 'unknown'}, 'minimax-h3-image': {'state': 'ready'}}}
            write_availability(data, status)
            self.assertEqual(preferred_ready('image', {'flux-image','minimax-h3-image'}, status_path=status, priority_path=priority), 'minimax-h3-image')
            data['observed_at'] = (datetime.now(timezone.utc)-timedelta(minutes=11)).isoformat()
            write_availability(data, status)
            self.assertIsNone(preferred_ready('image', {'minimax-h3-image'}, status_path=status, priority_path=priority))
            self.assertIsNone(read_fresh_availability(status))

    def test_duplicate_and_unsupported_priority_rejected(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'priority.json'
            for image in (['flux-image','flux-image'], ['other']):
                path.write_text(json.dumps({'schema_version':1,'image':image,'video_first_frame':['minimax-h3-i2v']}))
                with self.assertRaises(ValueError): read_priorities(path)

    def test_collection_never_hashes_weights_and_preserves_catalog_identity(self):
        with patch('hashlib.file_digest', side_effect=AssertionError('weight hash called')):
            data = collect_availability()
        self.assertTrue(any(item['id'] == 'flux-klein' for item in data['models']))
        self.assertIn('minimax-h3-image', data['services'])
        self.assertIn('downloads', data)


if __name__ == '__main__':
    unittest.main()
