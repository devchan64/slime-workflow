import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from generators.wan21_t2v.import_kxsr import import_kxsr

class KxsrImportTest(unittest.TestCase):
    def test_verified_file_is_imported_without_overwriting(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input';source.write_bytes(b'weights')
            target=root/'models'/'kxsr.safetensors';digest=hashlib.sha256(b'weights').hexdigest()
            self.assertEqual(import_kxsr(source,target,digest),target)
            self.assertEqual(target.read_bytes(),b'weights')
            with self.assertRaises(FileExistsError): import_kxsr(source,target,digest)
            self.assertEqual(target.read_bytes(),b'weights')
    def test_bad_hash_or_symlink_never_publishes(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input';source.write_bytes(b'weights');target=root/'out'/'kxsr.safetensors'
            with self.assertRaisesRegex(ValueError,'SHA-256'):import_kxsr(source,target,'0'*64)
            self.assertFalse(target.exists());self.assertEqual(list(target.parent.iterdir()),[])
            link=root/'link';link.symlink_to(source)
            with self.assertRaises(OSError):import_kxsr(link,target,hashlib.sha256(b'weights').hexdigest())
            self.assertFalse(target.exists())

if __name__=='__main__':unittest.main()
