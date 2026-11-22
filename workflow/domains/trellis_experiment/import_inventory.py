"""Inventory Python distributions imported by a CPU pipeline-import probe."""
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / ".local/trellis-experiment"


def main(output):
    os.environ["ATTN_BACKEND"] = "sdpa"
    os.environ["HF_HUB_OFFLINE"] = "1"
    sys.path[:0] = [str(LOCAL / "trellis-strix-halo-2794cbbd05c921876ebff354af5a67f447f5b7a9"),
                    str(LOCAL / "TRELLIS-193e0502b5cb3eb5997ec457d5340e95d09b158e")]
    from runners.trellis import shims
    shims.install()
    from trellis.pipelines import TrellisImageTo3DPipeline  # noqa: F401

    mapping = metadata.packages_distributions()
    roots = sorted({name.split(".", 1)[0] for name in sys.modules})
    names = sorted({distribution for root in roots for distribution in mapping.get(root, ())})
    rows = []
    for name in names:
        try:
            package = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        rows.append({"name": name, "version": package.version,
                     "license_expression": package.metadata.get("License-Expression"),
                     "license_metadata": package.metadata.get("License"),
                     "license_files": [str(x) for x in package.files or ()
                                       if "licen" in str(x).lower() or str(x).lower().endswith("copying")],
                     "license_classifiers": [x for x in package.metadata.get_all("Classifier", [])
                                             if x.startswith("License ::")]})
    result = {"scope": "CPU pipeline import only; excludes model load, inference and all other paths",
              "note": "Import-to-distribution mapping is heuristic; metadata is not a legal audit.",
              "import_roots": roots, "distributions": rows}
    with Path(output).open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2)
        file.write("\n")
    print(f"import roots: {len(roots)}; associated distributions: {len(rows)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: import_inventory.py OUTPUT.json")
    main(sys.argv[1])
