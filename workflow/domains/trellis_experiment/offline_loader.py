"""Load the pinned DINOv2 encoder without torch hub downloads."""
import hashlib
from pathlib import Path

DINO_REVISION = "7764ea0f912e53c92e82eb78a2a1631e92725fc8"
DINO_SHA256 = "36e4deffbaef061a2576705b0c36f93621e2ae20bf6274694821b0b492551b51"
WORKFLOW_ROOT = Path(__file__).resolve().parents[3]


def install_local_dino(pipeline_class):
    """Replace the pipeline's image encoder initializer before loading weights."""
    import torch
    from torchvision import transforms

    source = WORKFLOW_ROOT / ".local/trellis-experiment" / f"dinov2-{DINO_REVISION}"
    weights = WORKFLOW_ROOT / ".model/trellis-dinov2/dinov2_vitl14_reg4_pretrain.pth"
    if not (source / "hubconf.py").is_file() or not weights.is_file() or weights.is_symlink():
        raise FileNotFoundError("DINOv2 소스 또는 가중치가 없습니다")
    with weights.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != DINO_SHA256:
            raise ValueError("DINOv2 가중치 해시 불일치")

    def init_local(self, name):
        if name != "dinov2_vitl14_reg":
            raise ValueError(f"지원하지 않는 이미지 인코더: {name}")
        model = torch.hub.load(str(source), name, source="local", pretrained=False)
        state = torch.load(weights, map_location="cpu", weights_only=True)
        model.load_state_dict(state, strict=True)
        model.eval()
        self.models["image_cond_model"] = model
        self.image_cond_model_transform = transforms.Compose([
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    pipeline_class._init_image_cond_model = init_local


def load_local_pipeline(pipeline_class, model_dir):
    """Load only local model paths without the upstream catch-all Hub fallback."""
    import json
    from trellis import models
    from trellis.pipelines.base import Pipeline

    model_dir = Path(model_dir).resolve(strict=True)
    config = json.loads((model_dir / "pipeline.json").read_text(encoding="utf-8"))
    args = config["args"]
    loaded = {}
    for name, relative in args["models"].items():
        base = (model_dir / relative).resolve()
        if not base.is_relative_to(model_dir):
            raise ValueError(f"모델 경로가 범위를 벗어납니다: {relative}")
        if not base.with_suffix(".json").is_file() or not base.with_suffix(".safetensors").is_file():
            raise FileNotFoundError(f"모델 파일 누락: {relative}")
        loaded[name] = models.from_pretrained(str(base))
    base_pipeline = Pipeline(loaded)
    base_pipeline._pretrained_args = args
    # The upstream constructor initializes no models when called without arguments.
    result = pipeline_class()
    result.__dict__ = base_pipeline.__dict__
    from trellis.pipelines import samplers
    for key in ("sparse_structure_sampler", "slat_sampler"):
        spec = args[key]
        setattr(result, key, getattr(samplers, spec["name"])(**spec["args"]))
        setattr(result, key + "_params", spec["params"])
    result.slat_normalization = args["slat_normalization"]
    result._init_image_cond_model(args["image_cond_model"])
    return result
