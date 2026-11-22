"""Queue the small GPU shim comparison without bypassing the shared reservation."""
import os
from pathlib import Path
import runpy
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
TEST = ROOT / ".local/trellis-experiment/trellis-strix-halo-2794cbbd05c921876ebff354af5a67f447f5b7a9/tests/test_shims.py"
EXPERIMENT = ROOT / ".local/trellis-experiment"


def load_probe():
    import torch
    os.environ["ATTN_BACKEND"] = "sdpa"
    os.environ["SPARSE_BACKEND"] = "spconv"
    os.environ["SPARSE_ATTN_BACKEND"] = "flash_attn"
    os.environ["HF_HUB_OFFLINE"] = "1"
    sys.path[:0] = [str(EXPERIMENT / "trellis-strix-halo-2794cbbd05c921876ebff354af5a67f447f5b7a9"),
                    str(EXPERIMENT / "TRELLIS-193e0502b5cb3eb5997ec457d5340e95d09b158e")]
    from runners.trellis import shims
    shims.install()
    from trellis.pipelines import TrellisImageTo3DPipeline
    from workflow.domains.trellis_experiment.offline_loader import install_local_dino, load_local_pipeline
    install_local_dino(TrellisImageTo3DPipeline)
    pipeline = load_local_pipeline(TrellisImageTo3DPipeline, ROOT / ".model/trellis-image-large")
    pipeline.cuda()
    for name, model in pipeline.models.items():
        count = 0
        for parameter in model.parameters():
            if not torch.isfinite(parameter).all().item():
                raise ValueError(f"비유한 가중치: {name}")
            count += parameter.numel()
        print(f"model={name} parameters={count} finite=true", flush=True)
    torch.cuda.synchronize()
    print("GPU 모델 적재 및 파라미터 유한값 검사 완료", flush=True)


def main():
    if len(sys.argv) == 2 and sys.argv[1] in ("--worker", "--load-worker"):
        reservation = os.environ.get("SLIME_GPU_RESERVATION_PATH")
        if not reservation or not Path(reservation).is_file():
            raise RuntimeError("공용 GPU 예약이 필요합니다")
        import torch
        if not torch.version.hip or not torch.cuda.is_available():
            raise RuntimeError("ROCm GPU를 사용할 수 없습니다")
        if sys.argv[1] == "--load-worker":
            load_probe()
        else:
            runpy.run_path(str(TEST), run_name="__main__")
        return
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] != "--load"):
        raise ValueError("알 수 없는 인자")
    if not TEST.is_file():
        raise FileNotFoundError(TEST)
    from workflow.common.gpu_job_queue import launch_gpu_process
    job = ROOT / ".tmp/trellis-experiment" / ("gpu-probe-" + uuid.uuid4().hex)
    job.mkdir(parents=True, exist_ok=False)
    with (job / "worker.log").open("w", encoding="utf-8") as log:
        worker = "--load-worker" if len(sys.argv) == 2 else "--worker"
        process = launch_gpu_process([sys.executable, str(Path(__file__).resolve()), worker], job, "trellis-experiment", stdout=log, stderr=log, start_new_session=True)
    print(f"job={job} queue_pid={process.pid}")


if __name__ == "__main__":
    main()
