import json
from pathlib import Path
import tempfile
import unittest

from workflow.common.model_catalog import read_minimax_complete_observation, read_partial_prefix_survey
from workflow.common.model_partial_prefix_survey import CANDIDATES, compare_prefix


class PartialPrefixSurveyTest(unittest.TestCase):
    def test_match_mismatch_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); partial = root/'part'; final = root/'final'
            final.write_bytes(b'abcdef'); partial.write_bytes(b'abc')
            self.assertEqual(compare_prefix(partial, final, 6)['status'], 'matches')
            partial.write_bytes(b'abx')
            self.assertEqual(compare_prefix(partial, final, 6)['status'], 'different')
            partial.unlink(); partial.symlink_to(final)
            with self.assertRaises(ValueError): compare_prefix(partial, final, 6)

    def test_historical_report_rejects_escape_and_bad_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'record.json'
            records = []
            for model, relative, size, _etag, _cache in CANDIDATES:
                records.append({'model':model,'final_path':f'{model}/{relative}', 'partial_path':f'{model}/.cache/huggingface/download/a.incomplete',
                                'status':'matches','prefix_bytes':1,'final_bytes':size})
            report = {'version':1,'observed_at':'then','records':records}
            path.write_text(json.dumps(report)); self.assertIsNotNone(read_partial_prefix_survey(path))
            records[0]['partial_path'] = records[0]['model']+'/.cache/huggingface/download/../../other.incomplete'
            path.write_text(json.dumps(report)); self.assertIsNone(read_partial_prefix_survey(path))
            records[0]['partial_path'] = records[0]['model']+'/.cache/huggingface/download/a.incomplete'
            records[0]['prefix_bytes'] = -1
            path.write_text(json.dumps(report)); self.assertIsNone(read_partial_prefix_survey(path))

    def test_complete_file_observation_does_not_accept_false_match(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'record.json'
            entries = []
            for model, relative, size, digest, _cache in CANDIDATES:
                entries.append({'model':model,'path':relative,'size':size,'sha256':digest,'snapshot_id':'a'*32,
                                'matches_pinned':True,'matches_recorded_snapshot_hash':True})
            record = {'observed_at':'then','files':entries}
            path.write_text(json.dumps(record)); self.assertIsNotNone(read_minimax_complete_observation(path))
            entries[0]['sha256'] = '0'*64
            path.write_text(json.dumps(record)); self.assertIsNone(read_minimax_complete_observation(path))

    def test_current_identity_distinguishes_changed_and_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); entries = []
            identity = lambda item: [item.st_dev,item.st_ino,item.st_size,item.st_mtime_ns,item.st_ctime_ns]
            for model, relative, size, _etag, cache in CANDIDATES:
                final = root/model/relative; final.parent.mkdir(parents=True, exist_ok=True)
                with final.open('wb') as stream: stream.truncate(size)
                partial = root/model/cache/'part.incomplete'; partial.parent.mkdir(parents=True, exist_ok=True)
                partial.write_bytes(b'x')
                entries.append({'model':model, 'final_path':final.relative_to(root).as_posix(),
                    'partial_path':partial.relative_to(root).as_posix(), 'status':'matches', 'prefix_bytes':1,
                    'final_bytes':size, 'partial_identity':identity(partial.stat()),'final_identity':identity(final.stat())})
            record = root/'record.json'; record.write_text(json.dumps({'version':1,'observed_at':'then','records':entries}))
            self.assertTrue(all(x['current_identity']=='matches' for x in read_partial_prefix_survey(record,model_root=root)['records']))
            (root/entries[0]['partial_path']).write_bytes(b'changed')
            (root/entries[1]['partial_path']).unlink()
            states = [x['current_identity'] for x in read_partial_prefix_survey(record,model_root=root)['records']]
            self.assertEqual(states,['changed','unavailable'])
