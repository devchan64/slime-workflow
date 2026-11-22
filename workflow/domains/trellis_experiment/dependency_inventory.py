"""Record selected installed package metadata; this is not a complete audit."""
import importlib.metadata as metadata
import json
import sys
from pathlib import Path

PACKAGES = ("torch", "torchvision", "numpy", "Pillow", "scipy", "trimesh", "opencv-python-headless",
            "easydict", "safetensors", "utils3d", "rembg", "onnxruntime", "timm", "transformers",
            "huggingface-hub", "einops", "plyfile")


def inventory():
    rows = []
    for name in PACKAGES:
        try:
            package = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            rows.append({"name": name, "installed": False})
            continue
        rows.append({"name": name, "version": package.version,
                     "license_expression": package.metadata.get("License-Expression"),
                     "license_classifier": [item for item in package.metadata.get_all("Classifier", [])
                                            if item.startswith("License ::")],
                     "license_files": [str(path) for path in package.files or () if "licen" in str(path).lower() or str(path).lower().endswith("copying")]})
    return {"note": "Selected installed metadata only; not proof of imports, transitive dependencies, or legal clearance.", "packages": rows}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: dependency_inventory.py OUTPUT.json")
    target = Path(sys.argv[1])
    with target.open("x", encoding="utf-8") as stream:
        json.dump(inventory(), stream, indent=2)
        stream.write("\n")
