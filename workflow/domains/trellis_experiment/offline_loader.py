"""Load the pinned DINOv2 encoder without torch hub downloads."""
import hashlib
import json
from pathlib import Path

DINO_REVISION = "7764ea0f912e53c92e82eb78a2a1631e92725fc8"
DINO_SHA256 = "36e4deffbaef061a2576705b0c36f93621e2ae20bf6274694821b0b492551b51"
WORKFLOW_ROOT = Path(__file__).resolve().parents[3]
DINO_FILENAME = 'dinov2_vitl14_reg4_pretrain.pth'
TRELLIS_ID = 'microsoft/TRELLIS-image-large'
TRELLIS_REVISION = '25e0d31ffbebe4b5a97464dd851910efc3002d96'


def resolve_trellis_model(model_root=None):
    root = Path(model_root) if model_root is not None else WORKFLOW_ROOT / '.model'
    candidate = root / 'models' / 'trellis-image-large'
    marker = candidate / '.catalog-migration.json'
    original = root / 'trellis-image-large'
    retained = root.parent / '.local/model-catalog/retained/trellis-image-large/original'
    def fallback():
        if original.is_dir() and not original.is_symlink():
            return original
        if retained.is_dir() and not any(p.is_symlink() for p in (retained, *retained.parents)):
            return retained
        return original
    try:
        if candidate.parent.is_symlink() or candidate.is_symlink() or marker.is_symlink() or marker.stat().st_size > 4096:
            return fallback()
        record = json.loads(marker.read_text(encoding='utf-8'))
        if (record.get('schema_version') == 1 and record.get('model_id') == TRELLIS_ID
                and record.get('revision') == TRELLIS_REVISION and record.get('state') == 'verified'
                and (candidate / 'pipeline.json').is_file() and not (candidate / 'pipeline.json').is_symlink()):
            return candidate
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return fallback()


def resolve_dino_weights(model_root=None):
    root = Path(model_root) if model_root is not None else WORKFLOW_ROOT / '.model'
    new_parent = root / 'models' / 'trellis-dinov2'
    candidate = new_parent / DINO_FILENAME
    if (not new_parent.parent.is_symlink() and not new_parent.is_symlink()
            and not candidate.is_symlink() and candidate.is_file()):
        return candidate
    original = root / 'trellis-dinov2' / DINO_FILENAME
    if original.is_file() and not original.is_symlink():
        return original
    retained = root.parent / '.local/model-catalog/retained/trellis-dinov2/original' / DINO_FILENAME
    if (not retained.is_symlink() and not retained.parent.is_symlink()
            and not retained.parent.parent.is_symlink() and retained.is_file()):
        return retained
    return original


def install_local_dino(pipeline_class):
    """Replace the pipeline's image encoder initializer before loading weights."""
    import torch
    from torchvision import transforms

    source = WORKFLOW_ROOT / ".local/trellis-experiment" / f"dinov2-{DINO_REVISION}"
    weights = resolve_dino_weights()
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
    return weights


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
