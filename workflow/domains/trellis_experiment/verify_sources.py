"""Compare prepared source trees to recorded downloaded archives without execution."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[3] / ".local/trellis-experiment"
SOURCES = (
    ("trellis-193e0502.tar.gz", "d1b2883287085757c1d40fc886e7c10d4c3b4218b851aafd277dd48bf079f52e"),
    ("flexicubes-815e075.tar.gz", "96ac575e8d035c139f2aed8ad876fa5bc38fa81b7ea2c5de46440dd044e4e00e"),
    ("dinov2-7764ea0f.tar.gz", "c27dcdaf50e9fb5bbdf2bb529da357716372e19c6afab17d5350f3f0094aed4b"),
    ("strix-2794cbbd.tar.gz", "d7cd1f2af2071aedd0a02b6592ab3d121a776e814cd8009fad7e5d1c128e3d14"),
)


def digest(stream):
    return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    records = []
    for name, expected in SOURCES:
        path = ROOT / name
        with path.open("rb") as stream:
            if digest(stream) != expected:
                raise ValueError(f"아카이브 해시 불일치: {name}")
        count = 0
        with tarfile.open(path, "r:gz") as archive:
            for entry in archive:
                if not entry.isfile():
                    continue
                relative = Path(entry.name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"잘못된 아카이브 경로: {entry.name}")
                targets = [ROOT / relative]
                if name == "flexicubes-815e075.tar.gz":
                    targets.append(ROOT / "TRELLIS-193e0502b5cb3eb5997ec457d5340e95d09b158e/trellis/representations/mesh/flexicubes" / Path(*relative.parts[1:]))
                original = archive.extractfile(entry)
                if original is None:
                    raise ValueError(f"아카이브 파일 읽기 실패: {entry.name}")
                with original:
                    original_hash = digest(original)
                for target in targets:
                    if target.is_symlink() or not target.is_file():
                        raise ValueError(f"소스 파일 누락 또는 링크: {target}")
                    with target.open("rb") as actual:
                        if original_hash != digest(actual):
                            raise ValueError(f"소스 내용 변경: {target}")
                count += 1
        records.append({"archive": name, "sha256": expected, "matching_regular_files": count})
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
