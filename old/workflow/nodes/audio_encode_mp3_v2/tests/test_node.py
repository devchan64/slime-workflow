import json
import unittest
from pathlib import Path

class AudioEncodeMp3V2Test(unittest.TestCase):
    def test_package_exists(self):
        p = Path("workflow/nodes/audio_encode_mp3_v2/packages/unit-audio-encode-mp3-v2.json")
        self.assertTrue(p.is_file())
        obj = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(obj["node_id"], "music.audio.encode.mp3")

if __name__ == "__main__":
    unittest.main()
