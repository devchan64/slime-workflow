"""Import a locally supplied KXSR LoRA after checking its published SHA-256."""
import argparse
import hashlib
import os
from pathlib import Path
import stat
import tempfile

from generators.wan21_t2v.assets import BOSS_LORA, BOSS_SHA256


def import_kxsr(source, destination=BOSS_LORA, expected_sha256=BOSS_SHA256):
    source=Path(source); destination=Path(destination)
    flags=os.O_RDONLY | getattr(os,'O_NOFOLLOW',0) | getattr(os,'O_NONBLOCK',0)
    descriptor=os.open(source,flags)
    temporary=None
    try:
        with os.fdopen(descriptor,'rb') as input_stream:
            info=os.fstat(input_stream.fileno())
            if not stat.S_ISREG(info.st_mode): raise ValueError('LoRA 원본은 일반 파일이어야 합니다.')
            if destination.is_symlink() or destination.exists(): raise FileExistsError('기존 KXSR 파일은 덮어쓰지 않습니다.')
            destination.parent.mkdir(parents=True,exist_ok=True)
            fd,temporary_name=tempfile.mkstemp(prefix='.kxsr-',suffix='.partial',dir=destination.parent)
            temporary=Path(temporary_name)
            digest=hashlib.sha256()
            with os.fdopen(fd,'wb') as output:
                for chunk in iter(lambda:input_stream.read(1024*1024),b''):
                    output.write(chunk);digest.update(chunk)
                output.flush();os.fsync(output.fileno())
            after=os.fstat(input_stream.fileno())
            if (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
                raise ValueError('복사 중 LoRA 원본이 변경됐습니다.')
            if digest.hexdigest()!=expected_sha256:
                raise ValueError('KXSR SHA-256이 일치하지 않습니다.')
            os.link(temporary,destination,follow_symlinks=False)
            temporary.unlink();temporary=None
            directory_fd=os.open(destination.parent,os.O_RDONLY | getattr(os,'O_DIRECTORY',0))
            try: os.fsync(directory_fd)
            finally: os.close(directory_fd)
            return destination
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path,help='Path to wan-1.3B-Bossfight.safetensors')
    args=parser.parse_args()
    print(import_kxsr(args.source))


if __name__=='__main__': main()
