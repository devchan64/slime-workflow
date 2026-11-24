"""Verify official TRELLIS checkpoint hashes against its pinned Hub revision."""
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import urlopen

REVISION = "25e0d31ffbebe4b5a97464dd851910efc3002d96"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from workflow.domains.trellis_experiment.offline_loader import resolve_trellis_model


def main():
    model_dir = resolve_trellis_model()
    with urlopen(f"https://huggingface.co/api/models/microsoft/TRELLIS-image-large/revision/{REVISION}?blobs=true", timeout=30) as response:
        meta = json.load(response)
    if meta["sha"] != REVISION:
        raise RuntimeError("모델 리비전 불일치")
    records = []
    for entry in meta["siblings"]:
        path = model_dir / entry["rfilename"]
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"파일 누락 또는 심볼릭 링크: {path}")
        if path.stat().st_size != entry["size"]:
            raise RuntimeError(f"크기 불일치: {path}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        expected = entry.get("lfs", {}).get("sha256")
        if expected and digest != expected:
            raise RuntimeError(f"SHA-256 불일치: {path}")
        if not expected:
            blob_hash = hashlib.sha1(b"blob " + str(path.stat().st_size).encode() + b"\0" + path.read_bytes()).hexdigest()
            if blob_hash != entry["blobId"]:
                raise RuntimeError(f"Git blob 불일치: {path}")
        records.append({"path": entry["rfilename"], "size": entry["size"], "sha256": digest})
    report = {"repository": "microsoft/TRELLIS-image-large", "revision": REVISION, "files": records}
    output = model_dir / "verified-manifest.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"검증 완료: {len(records)}개 파일, {output}")


if __name__ == "__main__":
    main()
