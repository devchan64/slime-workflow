import subprocess
import sys
import tempfile
import unittest
from generators.animation.anny_render_process import run_blender_render


class AnnyRenderProcessTests(unittest.TestCase):
    def test_success_and_failure_propagate(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(run_blender_render([sys.executable,'-c','pass'],directory,2).returncode,0)
            with self.assertRaises(subprocess.CalledProcessError):
                run_blender_render([sys.executable,'-c','raise SystemExit(3)'],directory,2)

    def test_hung_process_is_reaped(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError,'제한 시간'):
                run_blender_render([sys.executable,'-c','import time;time.sleep(30)'],directory,.1)
