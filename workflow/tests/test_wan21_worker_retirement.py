from pathlib import Path
import subprocess
import sys
import unittest


class RetiredWan21WorkerTest(unittest.TestCase):
    def test_script_and_imported_executor_reject_new_generation(self):
        from generators.wan21_t2v import worker as text_worker
        from generators.wan21_i2v import worker as image_worker
        root = Path(__file__).resolve().parents[2]
        for kind, worker in (('t2v', text_worker), ('i2v', image_worker)):
            with self.subTest(kind=kind):
                process = subprocess.run([sys.executable, str(root/'generators'/f'wan21_{kind}'/'worker.py')],
                                         cwd=root, text=True, capture_output=True, timeout=10)
                self.assertNotEqual(process.returncode, 0)
                self.assertIn('폐기', process.stderr)
                with self.assertRaisesRegex(RuntimeError, '폐기'):
                    worker.execute(None, None, None, None)
                self.assertTrue(str(worker.JOB_STORAGE).endswith(f'.tmp/test/wan21-{kind}'))
