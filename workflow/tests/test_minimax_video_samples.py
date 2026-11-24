"""로컬 격리 MP4의 실제 디코딩과 표본 선택 검증."""
import hashlib
import tempfile
import unittest
from pathlib import Path
import imageio_ffmpeg
from workflow.domains.hermes_agent.minimax_video_samples import extract


class MiniMaxVideoSamplesTests(unittest.TestCase):
    def test_decode_samples_from_final_mp4_and_reject_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);video=root/'sample.mp4';output=root/'frames';output.mkdir()
            writer=imageio_ffmpeg.write_frames(str(video),(32,32),fps=4,codec='libx264',macro_block_size=1)
            writer.send(None)
            try:
                for index in range(4):writer.send(bytes([index*50,0,0])*(32*32))
            finally:writer.close()
            digest=hashlib.sha256(video.read_bytes()).hexdigest()
            record=extract(video,digest,output)
            self.assertEqual(record['frames'],4)
            self.assertEqual([sample['frame'] for sample in record['samples']],[0,1,3])
            self.assertEqual(record['dimensions'],[32,32])
            self.assertTrue(all((output/item['filename']).is_file() for item in record['samples']))
            with self.assertRaises(ValueError):extract(video,'0'*64,output)
