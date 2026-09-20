"""노드 단일 실행을 컨테이너로 위임하기 위한 런너."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
import re
from typing import Any

from workflow.interfaces import PipelineContext


_NODE_ID_TO_SOURCE_DIR: dict[str, str] = {}


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    return value


def _swap_path_prefix(value: str, source: str, target: str) -> str:
    if not isinstance(value, str):
        return value
    normalized = value
    source = source.rstrip("/").rstrip("\\")
    if not source:
        return normalized
    if normalized == source:
        return target
    if normalized.startswith(f"{source}/") or normalized.startswith(f"{source}\\"):
        return f"{target}{normalized[len(source):]}"
    return normalized


def _walk_with_path_map(obj: Any, source: str, target: str) -> Any:
    if isinstance(obj, dict):
        return {str(key): _walk_with_path_map(item, source, target) for key, item in obj.items()}
    if isinstance(obj, list):
        return [_walk_with_path_map(item, source, target) for item in obj]
    if isinstance(obj, tuple):
        return [_walk_with_path_map(item, source, target) for item in obj]
    if isinstance(obj, str):
        mapped = _swap_path_prefix(obj, source, target)
        if mapped != obj:
            return mapped
        return obj
    return obj


def _host_to_container_path(value: Any, host_repo: Path, host_run_root: Path, container_repo: str, container_run_root: str) -> Any:
    host_repo = str(host_repo)
    host_run_root = str(host_run_root)
    mapped = _walk_with_path_map(value, host_run_root, container_run_root)
    mapped = _walk_with_path_map(mapped, host_repo, container_repo)
    return mapped


def _container_to_host_path(value: Any, host_repo: Path, host_run_root: Path, container_repo: str, container_run_root: str) -> Any:
    mapped = _walk_with_path_map(value, container_run_root, str(host_run_root))
    mapped = _walk_with_path_map(mapped, container_repo, str(host_repo))
    return mapped


def _build_node_executor(node_id: str):
    raise RuntimeError(f"지원하지 않는 node_id: {node_id}")


def _restore_node_payload(node_id: str, payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    return payload


def _collect_container_env() -> list[str]:
    env_keys = []
    for key in sorted(os.environ):
        if key.startswith("WORKFLOW_") or key.startswith("OLLAMA_"):
            env_keys.append(key)
    env_keys.extend(["PYTHONPATH", "HF_HOME", "HF_HUB_CACHE", "TRANSFORMERS_CACHE", "PATH"])
    return env_keys


def _to_argument_envs(env_keys: list[str]) -> list[str]:
    env_args: list[str] = []
    for key in env_keys:
        value = os.environ.get(key)
        if value is None:
            continue
        env_args.extend(["-e", f"{key}={value}"])
    return env_args


def _normalize_node_token(node_id: str) -> str:
    safe_node_id = re.sub(r"[^a-z0-9._-]", "-", str(node_id).lower().strip())
    safe_node_id = safe_node_id.strip("-.") or "node"
    return safe_node_id


def _resolve_dockerfile_path(raw_path: str, repo_root: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def _parse_csv_paths(raw: str) -> list[str]:
    values: list[str] = []
    if not raw:
        return values
    for chunk in raw.replace(";", ",").split(","):
        value = chunk.strip()
        if value:
            values.append(value)
    return values


def _build_file_fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha1()
    for path in sorted(paths):
        digest.update(str(path).encode("utf-8"))
        if not path.is_file():
            digest.update(b":missing:")
            continue
        digest.update(b":present:")
        digest.update(path.read_bytes())
    return digest.hexdigest()[:8]


def _resolve_node_hash_inputs(node_id: str, repo_root: Path) -> list[Path]:
    node_token = _normalize_node_token(node_id)
    node_key = node_token.upper().replace(".", "_").replace("-", "_")

    node_env_key = f"WORKFLOW_NODE_DOCKER_HASH_PATHS_{node_key}"
    node_overrides = _parse_csv_paths(str(os.getenv(node_env_key, "")).strip())
    global_overrides = _parse_csv_paths(str(os.getenv("WORKFLOW_NODE_DOCKER_HASH_PATHS", "")).strip())
    selected_overrides = node_overrides or global_overrides
    if selected_overrides:
        return [_resolve_dockerfile_path(raw, repo_root) for raw in selected_overrides]

    source_dir_rel = _NODE_ID_TO_SOURCE_DIR.get(node_id, "")
    if not source_dir_rel:
        return []
    source_dir = (repo_root / source_dir_rel).resolve()
    package_dir = source_dir / "packages"
    runtime_dir = source_dir / "runtime"
    application_dir = source_dir / "application"
    entrypoints_dir = source_dir / "entrypoints"

    hash_inputs: list[Path] = []
    if package_dir.is_dir():
        hash_inputs.extend(sorted(package_dir.glob("*.json")))
        requirements_path = package_dir / "requirements.txt"
        if requirements_path.is_file():
            hash_inputs.append(requirements_path)

    stage_path = application_dir / "stage.py"
    if stage_path.is_file():
        hash_inputs.append(stage_path)

    entrypoints_path = entrypoints_dir / "__init__.py"
    if entrypoints_path.is_file():
        hash_inputs.append(entrypoints_path)

    bootstrap_path = runtime_dir / "bootstrap.py"
    if bootstrap_path.is_file():
        hash_inputs.append(bootstrap_path)
    return hash_inputs


def _resolve_node_dockerfile_template(
    node_id: str,
    dockerfile_path: str | None = None,
) -> tuple[Path, str]:
    repo_root = Path(__file__).resolve().parents[2]
    if dockerfile_path:
        selected = _resolve_dockerfile_path(dockerfile_path, repo_root)
        if not selected.is_file():
            raise RuntimeError(f"지정한 노드 Dockerfile 경로가 없습니다: path={selected}")
        return selected, selected.read_text(encoding="utf-8")

    node_token = _normalize_node_token(node_id)
    profile = str(os.getenv("WORKFLOW_NODE_DOCKER_PROFILE", "")).strip().lower()

    direct_override = str(os.getenv("WORKFLOW_NODE_DOCKERFILE_PATH", "")).strip()
    if direct_override:
        selected = _resolve_dockerfile_path(direct_override, repo_root)
        if not selected.is_file():
            raise RuntimeError(f"지정한 Dockerfile 경로가 없습니다: {selected}")
        return selected, selected.read_text(encoding="utf-8")

    node_env_key = f"WORKFLOW_NODE_DOCKERFILE_{node_token.upper().replace('.', '_').replace('-', '_')}"
    node_override = str(os.getenv(node_env_key, "")).strip()
    if node_override:
        selected = _resolve_dockerfile_path(node_override, repo_root)
        if not selected.is_file():
            raise RuntimeError(f"지정한 노드 Dockerfile 경로가 없습니다: key={node_env_key}, path={selected}")
        return selected, selected.read_text(encoding="utf-8")

    source_dir_rel = _NODE_ID_TO_SOURCE_DIR.get(node_id, "")
    if not source_dir_rel:
        raise RuntimeError(f"node_id에 매핑된 소스 디렉터리가 없습니다: node_id={node_id}")
    node_docker_dir = (repo_root / source_dir_rel / "docker").resolve()

    candidates: list[Path] = []
    if profile:
        candidates.append(node_docker_dir / f"Dockerfile.{profile}")
        candidates.append(node_docker_dir / f"node-runtime.{profile}.Dockerfile")
    candidates.append(node_docker_dir / "Dockerfile")
    candidates.append(node_docker_dir / "node-runtime.Dockerfile")

    for candidate in candidates:
        if candidate.is_file():
            return candidate, candidate.read_text(encoding="utf-8")

    raise RuntimeError(
        "노드 Dockerfile 템플릿이 존재하지 않습니다. "
        "공용 Dockerfile fallback은 허용되지 않습니다. 노드 디렉터리에 Dockerfile을 구성하세요. "
        f"node_id={node_id}, profile={profile or '-'}, "
        f"expected={node_docker_dir / 'Dockerfile'}"
    )


def _build_node_image_name(node_id: str, base_image: str | None, dockerfile_content: str, node_input_hash: str) -> str:
    safe_node_id = _normalize_node_token(node_id)
    base_key = str(base_image).strip() if base_image is not None else "dockerfile-default"
    base_hash = hashlib.sha1(base_key.encode("utf-8")).hexdigest()[:8]
    dockerfile_hash = hashlib.sha1(dockerfile_content.encode("utf-8")).hexdigest()[:8]
    node_hash = str(node_input_hash or "00000000").strip()[:8] or "00000000"
    prefix = str(os.getenv("WORKFLOW_NODE_DOCKER_IMAGE_PREFIX", "workflow-node")).strip() or "workflow-node"
    return f"{prefix}:{safe_node_id}-{base_hash}-{dockerfile_hash}-{node_hash}"


def _docker_image_exists(docker_path: str, image: str) -> bool:
    completed = subprocess.run(
        [docker_path, "image", "inspect", image],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _parse_bool_env(name: str, default: bool = False) -> bool:
    value = str(os.getenv(name, "")).strip().lower()
    if value in {"", "auto"}:
        return default
    if value in {"1", "true", "on", "yes", "y"}:
        return True
    if value in {"0", "false", "off", "no", "n"}:
        return False
    return default


def _run_docker_build(docker_path: str, command: list[str], *, node_id: str) -> tuple[int, list[str]]:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if process.stdout is None:
        completed = process.wait()
        return completed, []

    collected: list[str] = []
    for line in process.stdout:
        line = line.rstrip()
        if not line:
            continue
        print(f"[ai-workflow] [node-docker-build] [INFO] node_id={node_id}, {line}", flush=True)
        collected.append(line)
    return_code = process.wait()
    return return_code, collected


def _run_docker_run(docker_path: str, command: list[str], *, node_id: str) -> tuple[int, list[str]]:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if process.stdout is None:
        return_code = process.wait()
        return return_code, []

    collected: list[str] = []
    for raw_line in process.stdout:
        line = raw_line.rstrip()
        if not line:
            continue
        print(f"[ai-workflow] [node-docker-run] [INFO] node_id={node_id}, {line}", flush=True)
        collected.append(line)

    return_code = process.wait()
    return return_code, collected


def ensure_node_docker_image(
    *,
    node_id: str,
    base_image: str | None = None,
    force: bool | None = None,
    dockerfile_path: str | None = None,
) -> str:
    """노드별 컨테이너 이미지를 보장한다."""
    docker_path = shutil.which("docker")
    if not docker_path:
        raise RuntimeError("docker 실행 파일이 없어 노드 컨테이너 이미지 빌드를 진행할 수 없습니다.")
    repo_root = Path(__file__).resolve().parents[2]
    dockerfile_path, dockerfile_content = _resolve_node_dockerfile_template(
        node_id,
        dockerfile_path=dockerfile_path,
    )
    node_hash_inputs = _resolve_node_hash_inputs(node_id=node_id, repo_root=repo_root)
    node_input_hash = _build_file_fingerprint(node_hash_inputs)
    target_image = _build_node_image_name(
        node_id=node_id,
        base_image=base_image,
        dockerfile_content=dockerfile_content,
        node_input_hash=node_input_hash,
    )
    force_build = _parse_bool_env("WORKFLOW_NODE_DOCKER_BUILD_FORCE", False) if force is None else force

    if _docker_image_exists(docker_path, target_image) and not force_build:
        return target_image

    with tempfile.TemporaryDirectory(prefix="workflow-node-docker-") as temp_dir:
        temp_root = Path(temp_dir)
        dockerfile = temp_root / "Dockerfile"
        dockerfile.write_text(dockerfile_content, encoding="utf-8")

        build_command: list[str] = [docker_path, "build"]
        if base_image:
            build_command.extend(["--build-arg", f"BASE_IMAGE={base_image}"])
        build_command.extend(["-t", target_image, "-f", str(dockerfile), str(temp_root)])

        return_code, build_logs = _run_docker_build(
            docker_path,
            build_command,
            node_id=node_id,
        )
        if return_code != 0:
            full_log = "\n".join(build_logs[-200:])
            raise RuntimeError(
                "노드별 Docker 이미지 빌드에 실패했습니다. "
                f"node_id={node_id}, base_image={base_image}, dockerfile={dockerfile_path}, "
                f"target_image={target_image}, "
                f"code={return_code}, stdout={full_log}"
            )

    return target_image


def run_node_in_container(
    *,
    node_id: str,
    context: PipelineContext,
    node_input: Any,
    run_root: str,
    docker_image: str | None = None,
    dockerfile_path: str | None = None,
    host_repo_root: str | Path | None = None,
    container_repo_root: str = "/workspace",
    container_run_root: str = "/workspace/run",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """단일 노드를 컨테이너에서 실행한다."""
    docker_path = shutil.which("docker")
    if not docker_path:
        raise RuntimeError("docker 실행 파일이 없어 노드 컨테이너 실행을 진행할 수 없습니다.")

    base_image = str(docker_image).strip() if docker_image is not None else None
    if base_image == "":
        base_image = None
    image = ensure_node_docker_image(
        node_id=node_id,
        base_image=base_image,
        dockerfile_path=dockerfile_path,
    )
    if not image:
        raise RuntimeError("WORKFLOW_NODE_DOCKER_IMAGE가 비어 있습니다.")

    host_repo_root_path = Path(host_repo_root or Path(__file__).resolve().parents[2]).resolve()
    host_run_root = Path(run_root).resolve()
    host_run_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="workflow-node-") as temp_dir:
        temp_root = Path(temp_dir)
        container_temp_root = "/tmp/workflow-node"
        (temp_root / "home").mkdir(parents=True, exist_ok=True)
        (temp_root / "pip-cache").mkdir(parents=True, exist_ok=True)

        host_input = temp_root / "node-input.json"
        host_output = temp_root / "node-output.json"
        host_context = temp_root / "node-context.json"

        containerized_input = _host_to_container_path(
            _to_jsonable(node_input),
            host_repo_root_path,
            host_run_root,
            container_repo_root,
            container_run_root,
        )
        containerized_context = _host_to_container_path(
            {
                "run_id": context.run_id,
                "run_root": str(host_run_root),
                "area": context.area,
                "pipeline": context.pipeline,
                "stage_logs": context.stage_logs,
            },
            host_repo_root_path,
            host_run_root,
            container_repo_root,
            container_run_root,
        )

        host_input.write_text(json.dumps(containerized_input, ensure_ascii=False, indent=2), encoding="utf-8")
        host_context.write_text(json.dumps(containerized_context, ensure_ascii=False, indent=2), encoding="utf-8")

        environment_args = _to_argument_envs(_collect_container_env())
        environment_args.extend(["-e", f"PYTHONPATH={container_repo_root}"])
        environment_args.extend(["-e", f"HOME={container_temp_root}/home"])
        environment_args.extend(["-e", f"PIP_CACHE_DIR={container_temp_root}/pip-cache"])

        command = [
            docker_path,
            "run",
            "--rm",
            "-i",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-w",
            container_repo_root,
            "-v",
            f"{host_repo_root_path}:{container_repo_root}",
            "-v",
            f"{host_run_root}:{container_run_root}",
            "-v",
            f"{temp_root}:{container_temp_root}",
            *environment_args,
            image,
            "python3",
            "-m",
            "workflow.core.node_docker_runner",
            "--node-id",
            node_id,
            "--input-path",
            f"{container_temp_root}/node-input.json",
            "--output-path",
            f"{container_temp_root}/node-output.json",
            "--context-path",
            f"{container_temp_root}/node-context.json",
        ]

        return_code, run_logs = _run_docker_run(
            docker_path,
            command,
            node_id=node_id,
        )
        if return_code != 0:
            logs = "\n".join(run_logs[-200:])
            raise RuntimeError(
                "노드 컨테이너 실행 실패: "
                f"node_id={node_id}, image={image}, code={return_code}, "
                f"stdout={logs}, stderr="
            )
        if not host_output.is_file():
            raise RuntimeError(f"노드 컨테이너 출력이 생성되지 않았습니다: {host_output}")

        raw_result = json.loads(host_output.read_text(encoding="utf-8"))
        if not isinstance(raw_result, dict):
            raise RuntimeError(f"노드 컨테이너 출력이 JSON 객체가 아닙니다: {host_output}")

    payload = raw_result.get("payload", raw_result)
    if not isinstance(payload, dict):
        raise RuntimeError(f"노드 컨테이너 결과가 JSON 객체가 아닙니다: {type(payload).__name__}")
    stage_logs = raw_result.get("stage_logs", [])
    if not isinstance(stage_logs, list):
        stage_logs = []
    restored = _container_to_host_path(
        payload,
        host_repo_root_path,
        host_run_root,
        container_repo_root,
        container_run_root,
    )
    return restored, stage_logs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="노드 단일 실행 worker")
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--context-path", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    node_id = str(args.node_id).strip()
    input_path = Path(str(args.input_path).strip())
    output_path = Path(str(args.output_path).strip())
    context_path = Path(str(args.context_path).strip())

    if not input_path.is_file():
        raise RuntimeError(f"노드 입력 파일이 없습니다: {input_path}")
    if not context_path.is_file():
        raise RuntimeError(f"노드 컨텍스트 파일이 없습니다: {context_path}")

    input_payload = json.loads(input_path.read_text(encoding="utf-8"))
    context_payload = json.loads(context_path.read_text(encoding="utf-8"))
    context = PipelineContext(
        run_id=str(context_payload.get("run_id", "")).strip() or "unknown",
        run_root=str(context_payload.get("run_root", "")).strip() or "",
        area=str(context_payload.get("area", "ai-workflow")).strip(),
        pipeline=context_payload.get("pipeline", "music"),
        stage_logs=list(context_payload.get("stage_logs", [])) if isinstance(context_payload.get("stage_logs", []), list) else [],
    )

    executor = _build_node_executor(node_id)
    restored_input = _restore_node_payload(node_id, input_payload)
    node_output = executor(context, restored_input)
    result = {
        "payload": _to_jsonable(node_output),
        "stage_logs": context.stage_logs,
    }
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
