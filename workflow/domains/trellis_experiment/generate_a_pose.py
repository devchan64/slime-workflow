"""Queue a mesh-only, eight-view TRELLIS experiment; never use upstream renderers."""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
LOCAL = ROOT / ".local/trellis-experiment"


def worker(job):
    reservation = os.environ.get("SLIME_GPU_RESERVATION_PATH")
    if not reservation or not Path(reservation).is_file():
        raise RuntimeError("공용 GPU 예약이 필요합니다")
    os.environ.update(ATTN_BACKEND="sdpa", SPARSE_BACKEND="spconv",
                      SPARSE_ATTN_BACKEND="flash_attn", HF_HUB_OFFLINE="1")
    sys.path[:0] = [str(LOCAL / "trellis-strix-halo-2794cbbd05c921876ebff354af5a67f447f5b7a9"),
                    str(LOCAL / "TRELLIS-193e0502b5cb3eb5997ec457d5340e95d09b158e")]
    import numpy as np
    import torch
    import trimesh
    from PIL import Image
    if not torch.version.hip or not torch.cuda.is_available():
        raise RuntimeError("ROCm GPU를 사용할 수 없습니다")
    from runners.trellis import shims
    shims.install()
    from trellis.pipelines import TrellisImageTo3DPipeline
    from workflow.domains.trellis_experiment.offline_loader import install_local_dino, load_local_pipeline
    install_local_dino(TrellisImageTo3DPipeline)
    pipeline = load_local_pipeline(TrellisImageTo3DPipeline, ROOT / ".model/trellis-image-large")
    pipeline.cuda()

    def check(label, value):
        if isinstance(value, torch.Tensor):
            if value.is_floating_point() and not torch.isfinite(value).all().item():
                raise ValueError(f"비유한 값: {label}")
        elif hasattr(value, "feats"):
            check(label + ".feats", value.feats)
        elif isinstance(value, (list, tuple)):
            for i, item in enumerate(value):
                check(f"{label}[{i}]", item)
        elif isinstance(value, dict):
            for key, item in value.items():
                check(f"{label}.{key}", item)

    for name in ("image_cond_model", "sparse_structure_flow_model", "sparse_structure_decoder", "slat_flow_model"):
        def hook(module, args, output, label=name):
            check(label, output)
        pipeline.models[name].register_forward_hook(hook)

    source = LOCAL / "masked-views-a-pose-v1"
    manifest = json.loads((source / "manifest.json").read_text())
    if len(manifest["views"]) != 8:
        raise ValueError("8개 참조 이미지가 필요합니다")
    images = []
    for item in manifest["views"]:
        path = source / item["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"입력 해시 불일치: {path}")
        with Image.open(path) as img:
            images.append(img.convert("RGBA"))
    print("generation: 8 views, seed 42, stochastic, 25+25 steps", flush=True)
    with torch.inference_mode():
        result = pipeline.run_multi_image(images, seed=42, formats=["mesh"], mode="stochastic")
    mesh = result["mesh"][0]
    check("mesh.vertices", mesh.vertices)
    check("mesh.vertex_attrs", mesh.vertex_attrs)
    vertices = mesh.vertices.detach().cpu().numpy()
    faces = mesh.faces.detach().cpu().numpy()
    if len(vertices) == 0 or len(faces) == 0 or faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError("비어 있거나 인덱스가 잘못된 메시")
    if not np.isfinite(vertices).all():
        raise ValueError("메시 정점 비유한값")
    # Capture the modules actually present after inference, before metadata imports
    # add more modules. Names include imports, not proof that every function ran.
    loaded_modules = {name: getattr(module, "__file__", None)
                      for name, module in list(sys.modules.items()) if module is not None}
    from importlib import metadata
    package_map = metadata.packages_distributions()
    package_names = sorted({dist for name in loaded_modules for dist in package_map.get(name.split(".", 1)[0], ())})
    packages = []
    for package_name in package_names:
        try:
            package = metadata.distribution(package_name)
        except metadata.PackageNotFoundError:
            continue
        packages.append({"name": package_name, "version": package.version,
                         "license_expression": package.metadata.get("License-Expression"),
                         "license_metadata": package.metadata.get("License"),
                         "license_files": [str(x) for x in package.files or ()
                                           if "licen" in str(x).lower() or str(x).lower().endswith("copying")]})
    (job / "runtime-imports.json").write_text(json.dumps({"modules": loaded_modules, "packages": packages,
        "limitations": "module presence does not prove code execution; distribution mapping may be incomplete"}, indent=2) + "\n")
    target = job / "mesh.ply"
    trimesh.Trimesh(vertices=vertices, faces=faces, process=False).export(target)
    report = {"input_manifest_sha256": hashlib.sha256((source / "manifest.json").read_bytes()).hexdigest(),
              "views": 8, "seed": 42, "mode": "stochastic", "steps": [25, 25],
              "torch": torch.__version__, "hip": torch.version.hip, "gpu": torch.cuda.get_device_name(0),
              "vertices": len(vertices), "faces": len(faces), "mesh_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
              "limitations": "raw geometry, no texture, no rig; provisional binary masks; A-pose view direction and pose consistency unverified"}
    (job / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False), flush=True)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        worker(Path(sys.argv[2]).resolve(strict=True))
        return
    if len(sys.argv) != 1:
        raise ValueError("알 수 없는 인자")
    from workflow.common.gpu_job_queue import launch_gpu_process
    job = ROOT / ".tmp/trellis-experiment" / ("generate-a-pose-" + uuid.uuid4().hex)
    job.mkdir(parents=True, exist_ok=False)
    with (job / "worker.log").open("w", encoding="utf-8") as log:
        process = launch_gpu_process([sys.executable, str(Path(__file__).resolve()), "--worker", str(job)], job,
                                     "trellis-experiment", stdout=log, stderr=log, start_new_session=True)
    print(f"job={job} queue_pid={process.pid}")


if __name__ == "__main__":
    main()
