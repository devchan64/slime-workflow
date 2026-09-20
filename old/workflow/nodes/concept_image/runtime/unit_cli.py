"""콘셉트 이미지 workflow 단위 실행 CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from workflow.core.node_prepare import ensure_required_files, run_prepare_command
from workflow.core.output_paths import local_runtime_output_path, local_run_root
from workflow.interfaces import PipelineContext, UnitIOContract, UnitPackageSpec, UnitPrepareContract
from workflow.nodes.concept_image.runtime.node_runner import run_concept_image_nodes, run_concept_image_unit


PACKAGE_FILES = {
    1: Path("workflow/nodes/concept_image/packages/unit-1-design-generate.json"),
    2: Path("workflow/nodes/concept_image/packages/unit-2-pixel-generate.json"),
    3: Path("workflow/nodes/concept_image/packages/unit-3-keyframe-compose.json"),
    4: Path("workflow/nodes/concept_image/packages/unit-4-animation-render.json"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="콘셉트 이미지 workflow 단위 실행기")
    parser.add_argument("--prompt", required=True, help="에셋 생성 프롬프트")
    parser.add_argument("--model-id", default="sd15-base", help="사용할 로컬 모델 식별자")
    parser.add_argument("--controlnet-id", default="", help="사용할 ControlNet 식별자")
    parser.add_argument("--ip-adapter-id", default="", help="사용할 IP-Adapter 식별자")
    parser.add_argument("--negative-prompt", default="", help="생성 억제용 네거티브 프롬프트")
    parser.add_argument("--generation-prompt", default="", help="모델 추론용 생성 프롬프트")
    parser.add_argument("--generation-negative-prompt", default="", help="모델 추론용 생성 네거티브 프롬프트")
    parser.add_argument("--style", default="rpg", help="아트 스타일")
    parser.add_argument("--seed", type=int, default=42, help="재현용 시드")
    parser.add_argument("--steps", type=int, default=28, help="추론 스텝 수")
    parser.add_argument("--guidance-scale", type=float, default=8.0, help="CFG 스케일")
    parser.add_argument("--ip-adapter-scale", type=float, default=0.55, help="IP-Adapter 영향도")
    parser.add_argument("--controlnet-conditioning-scale", type=float, default=1.0, help="ControlNet 영향도")
    parser.add_argument("--strength", type=float, default=0.35, help="img2img strength")
    parser.add_argument("--width", type=int, default=512, help="출력 폭")
    parser.add_argument("--height", type=int, default=512, help="출력 높이")
    parser.add_argument("--num-outputs", type=int, default=1, help="생성할 후보 이미지 수")
    parser.add_argument("--reference-image", action="append", default=[], help="참조 이미지 파일 경로")
    parser.add_argument("--reference-manifest", help="참조 이미지 목록 JSON 파일 경로")
    parser.add_argument("--control-image", help="ControlNet 조건 이미지 파일 경로")
    parser.add_argument("--ip-adapter-image", help="IP-Adapter 조건 이미지 파일 경로")
    parser.add_argument("--unit", type=int, choices=[1, 2, 3, 4], help="실행할 workflow 단위 노드 번호")
    parser.add_argument("--state-file", default=local_runtime_output_path("concept-image-state.json"), help="단위 실행 상태 파일 경로")
    parser.add_argument("--output", default=local_runtime_output_path("concept-image-result.json"), help="결과 JSON 파일 경로")
    parser.add_argument("--prepare-dependencies", action="store_true", help="패키지 의존성 설치 명령을 실행한다")
    parser.add_argument("--fetch-dependencies", action="store_true", help="패키지 의존성 가져오기 명령을 실행한다")
    parser.add_argument("--prepare-models", action="store_true", help="패키지 모델 준비 명령을 실행한다")
    parser.add_argument("--run-package-tests", action="store_true", help="노드 패키지 기본 테스트케이스를 검증하고 종료한다")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_unit_package(unit: int) -> UnitPackageSpec:
    path = PACKAGE_FILES.get(unit)
    if path is None:
        raise RuntimeError(f"지원하지 않는 concept-image unit이다: {unit}")
    if not path.is_file():
        raise RuntimeError(f"workflow 단위 패키지 매니페스트가 없다: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    io = raw.get("io", {})
    prepare = raw.get("prepare", {})
    return UnitPackageSpec(
        package_id=str(raw["package_id"]),
        version=str(raw["version"]),
        unit=int(raw["unit"]),
        node_id=str(raw["node_id"]),
        command=str(raw["command"]),
        io=UnitIOContract(
            required_inputs=list(io.get("required_inputs", [])),
            optional_inputs=list(io.get("optional_inputs", [])),
            outputs=list(io.get("outputs", [])),
            allowed_types=list(io.get("allowed_types", [])),
        ),
        prepare=UnitPrepareContract(
            dependency_files=list(prepare.get("dependency_files", [])),
            dependency_fetch_commands=list(prepare.get("dependency_fetch_commands", [])),
            install_commands=list(prepare.get("install_commands", [])),
            model_commands=list(prepare.get("model_commands", [])),
            required_model_ids=list(prepare.get("required_model_ids", [])),
        ),
        tests=list(raw.get("tests", [])),
    )


def _contract_type(entry: str) -> str:
    parts = str(entry).split(":", 1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise RuntimeError(f"잘못된 입출력 계약 항목이다: {entry}")
    return parts[1].strip()


def validate_io_contract(package: UnitPackageSpec) -> None:
    allowed = set(package.io.allowed_types)
    if not allowed:
        raise RuntimeError(f"패키지 allowed_types가 비어 있다: {package.package_id}")
    for section_name, entries in [
        ("required_inputs", package.io.required_inputs),
        ("optional_inputs", package.io.optional_inputs),
        ("outputs", package.io.outputs),
    ]:
        for entry in entries:
            item_type = _contract_type(entry)
            if item_type not in allowed:
                raise RuntimeError(
                    f"패키지 입출력 타입이 allowed_types에 없다: package={package.package_id}, section={section_name}, entry={entry}"
                )


def validate_payload_contract(package: UnitPackageSpec, payload: dict[str, Any]) -> None:
    missing: list[str] = []
    for entry in package.io.required_inputs:
        name = str(entry).split(":", 1)[0]
        if name == "prompt":
            if not str(payload.get("prompt", "")).strip():
                missing.append(entry)
        elif name == "state":
            continue
        elif name not in payload or payload.get(name) in (None, "", [], {}):
            missing.append(entry)
    if missing:
        raise RuntimeError(f"단위 패키지 필수 입력이 없다: package={package.package_id}, missing={missing}")


def validate_package_tests(package: UnitPackageSpec) -> None:
    if not package.tests:
        raise RuntimeError(f"노드 패키지 기본 테스트케이스가 없다: {package.package_id}")
    for index, test_case in enumerate(package.tests):
        if not isinstance(test_case, dict):
            raise RuntimeError(f"노드 패키지 테스트케이스는 객체여야 한다: package={package.package_id}, index={index}")
        test_id = str(test_case.get("id", "")).strip()
        test_type = str(test_case.get("type", "")).strip()
        if not test_id or not test_type:
            raise RuntimeError(f"노드 패키지 테스트케이스 id/type이 없다: package={package.package_id}, index={index}")
        input_fixture = test_case.get("input_fixture", {})
        if not isinstance(input_fixture, dict):
            raise RuntimeError(f"노드 패키지 테스트 input_fixture는 객체여야 한다: package={package.package_id}, test={test_id}")
        expected_outputs = test_case.get("expected_outputs", [])
        if not isinstance(expected_outputs, list) or not expected_outputs:
            raise RuntimeError(f"노드 패키지 테스트 expected_outputs가 비어 있다: package={package.package_id}, test={test_id}")


def _render_command(command: list[str], args: argparse.Namespace) -> list[str]:
    values = {"model_id": args.model_id}
    return [part.format(**values) for part in command]


def run_prepare_steps(package: UnitPackageSpec, args: argparse.Namespace, context: PipelineContext) -> None:
    prepare_step = "concept-image-prepare"
    ensure_required_files(
        context,
        step=prepare_step,
        files=package.prepare.dependency_files,
        package_id=package.package_id,
    )

    if args.fetch_dependencies:
        for command in package.prepare.dependency_fetch_commands:
            rendered = _render_command(command, args)
            run_prepare_command(
                context,
                step=prepare_step,
                phase="의존성 가져오기",
                command=rendered,
            )

    if args.prepare_dependencies:
        for command in package.prepare.install_commands:
            rendered = _render_command(command, args)
            run_prepare_command(
                context,
                step=prepare_step,
                phase="의존성 설치",
                command=rendered,
            )

    if args.prepare_models:
        for command in package.prepare.model_commands:
            rendered = _render_command(command, args)
            run_prepare_command(
                context,
                step=prepare_step,
                phase="모델 준비",
                command=rendered,
            )


def resolve_reference_images(cli_paths: list[str], manifest_path: str | None) -> list[dict[str, str]]:
    references: list[str] = list(cli_paths)
    if manifest_path:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        manifest_images = manifest.get("images", [])
        if not isinstance(manifest_images, list):
            raise RuntimeError("reference-manifest의 images는 배열이어야 한다")
        references.extend(str(item) for item in manifest_images)

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in references:
        value = str(raw).strip()
        if not value:
            continue
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError(f"참조 이미지 파일이 없다: {path}")
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"path": key, "name": path.name})
    return normalized


def build_run_id() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def resolve_run_root(args: argparse.Namespace, run_id: str) -> Path:
    default_output = Path(local_runtime_output_path("concept-image-result.json"))
    default_state = Path(local_runtime_output_path("concept-image-state.json"))
    output_path = Path(args.output)
    state_path = Path(args.state_file)
    if output_path.resolve() == default_output.resolve() and state_path.resolve() == default_state.resolve():
        return Path(local_run_root("concept-image", run_id))
    if output_path.parent == state_path.parent:
        return output_path.parent
    return output_path.parent


def base_payload(args: argparse.Namespace, run_id: str, run_root: Path, reference_images: list[dict[str, str]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "pipeline": "concept-image",
        "prompt": args.prompt,
        "model_id": args.model_id,
        "controlnet_id": args.controlnet_id,
        "ip_adapter_id": args.ip_adapter_id,
        "negative_prompt": args.negative_prompt,
        "generation_prompt": args.generation_prompt,
        "generation_negative_prompt": args.generation_negative_prompt,
        "style": args.style,
        "seed": args.seed,
        "steps": args.steps,
        "guidance_scale": args.guidance_scale,
        "ip_adapter_scale": args.ip_adapter_scale,
        "controlnet_conditioning_scale": args.controlnet_conditioning_scale,
        "strength": args.strength,
        "width": args.width,
        "height": args.height,
        "num_outputs": max(1, args.num_outputs),
        "run_id": run_id,
        "run_root": str(run_root),
        "reference_images": reference_images,
    }
    if args.control_image:
        payload["control_image_path"] = str(Path(args.control_image).expanduser().resolve())
    if args.ip_adapter_image:
        payload["ip_adapter_image_path"] = str(Path(args.ip_adapter_image).expanduser().resolve())
    return payload


def main() -> None:
    args = parse_args()
    run_id = build_run_id()
    run_root = resolve_run_root(args, run_id)
    output_path = Path(args.output)
    state_path = Path(args.state_file)
    if output_path == Path(local_runtime_output_path("concept-image-result.json")):
        output_path = run_root / "result.json"
    if state_path == Path(local_runtime_output_path("concept-image-state.json")):
        state_path = run_root / "state.json"

    package = load_unit_package(args.unit or 1)
    prepare_context = PipelineContext(run_id=run_id, run_root=str(run_root), pipeline="concept-image")
    validate_io_contract(package)
    validate_package_tests(package)
    if args.run_package_tests:
        print(f"패키지 테스트 검증 완료: package={package.package_id}, tests={len(package.tests)}")
        return
    run_prepare_steps(package, args, prepare_context)
    references = resolve_reference_images(args.reference_image, args.reference_manifest)
    save_json(
        run_root / "prompt.json",
        {
            "run_id": run_id,
            "pipeline": "concept-image",
            "unit": args.unit,
            "prompt": args.prompt,
            "model_id": args.model_id,
            "reference_images": references,
        },
    )

    if args.unit is None:
        payload = base_payload(args, run_id, run_root, references)
        validate_payload_contract(package, payload)
        result = run_concept_image_nodes(payload, run_id=run_id)
        result["mode"] = "all"
        result["package"] = {"package_id": package.package_id, "version": package.version}
        save_json(output_path, result)
        print(f"결과 저장 완료: {output_path}")
        return

    if args.unit == 1:
        payload = base_payload(args, run_id, run_root, references)
    else:
        state = load_json(state_path)
        payload = dict(state.get("result", {}))
        if not payload:
            raise RuntimeError("unit 2~4 실행 전에는 unit 1 결과(state-file)가 필요하다")
        payload["run_id"] = run_id
        payload["run_root"] = str(run_root)
        if references:
            payload["reference_images"] = references
        if args.control_image:
            payload["control_image_path"] = str(Path(args.control_image).expanduser().resolve())
        if args.ip_adapter_image:
            payload["ip_adapter_image_path"] = str(Path(args.ip_adapter_image).expanduser().resolve())

    validate_payload_contract(package, payload)
    state_obj = run_concept_image_unit(payload, args.unit, run_id=run_id)
    state_obj["package"] = {"package_id": package.package_id, "version": package.version}
    save_json(state_path, state_obj)
    save_json(output_path, state_obj)
    print(f"단계 실행 결과 저장 완료: unit={args.unit}, state={state_path}, output={output_path}")


if __name__ == "__main__":
    main()
