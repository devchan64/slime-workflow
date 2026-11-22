"""Check pinned official UniRig model checkpoints without deserializing them."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / ".model/unirig"
REVISION = "36842e2b5947e9e60f89275b83208c8e74071c63"
FILES = {
    "skeleton/articulation-xl_quantization_256/model.ckpt": (1439617174, "d8cf9b42d56e7bc316d293597ecf8c4c39a8631cdd44a261ecf388242fabd0f4"),
    "skin/articulation-xl/model.ckpt": (4375464854, "9d40cf42fb9d4c10d8b373d9f4f557c6fbbc5ebacae7ae6b3dce5a0d8a18bc33"),
}


def main():
    records = []
    for name, (size, expected) in FILES.items():
        path = MODEL / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
            raise ValueError(f"파일 누락 또는 크기 불일치: {name}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != expected:
            raise ValueError(f"SHA-256 불일치: {name}")
        records.append({"file": name, "size": size, "sha256": digest})
    report = {"repository": "VAST-AI/UniRig", "revision": REVISION, "files": records,
              "note": "Byte integrity only; checkpoints were not loaded or executed."}
    (MODEL / "verified-manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print("UniRig checkpoints: 2/2 SHA-256 verified")


if __name__ == "__main__":
    main()
