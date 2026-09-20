"""파이프라인 스펙 계약을 런타임에서 검증하기 위한 계약 유틸리티."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class PipelineContractError(RuntimeError):
    """스펙 계약 위반 시 발생."""


@dataclass(frozen=True)
class RuntimePipelineContract:
    pipeline_id: str
    input_contract: list[str]
    output_contract: list[str]
    runtime_executor: str
    node_ids: list[str]
    order: list[str]
    node_contracts: dict[str, Any]
    node_links: list[dict[str, Any]]


def _as_str_list(value: Any, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise PipelineContractError(f"{field_name}는 배열이어야 합니다")
    return [str(item).strip() for item in value if str(item).strip()]


def _require_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PipelineContractError(f"{path}는 객체여야 합니다")
    return value


def _as_dicts(value: Any, field_name: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise PipelineContractError(f"{field_name}는 배열이어야 합니다")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if isinstance(item, dict):
            result.append(_require_dict(item, f"{field_name}[{index}]"))
            continue
        raise PipelineContractError(f"{field_name}[{index}]는 객체여야 합니다")
    return result


def _as_str_dict(value: Any, field_name: str) -> dict[str, str]:
    if value is None:
        raise PipelineContractError(f"{field_name}는 객체여야 합니다")
    if not isinstance(value, dict):
        raise PipelineContractError(f"{field_name}는 객체여야 합니다")
    normalized: dict[str, str] = {}
    for key, raw_value in value.items():
        normalized[str(key).strip()] = str(raw_value).strip()
    if not normalized:
        raise PipelineContractError(f"{field_name}는 비어 있으면 안 됩니다")
    return normalized


def _parse_contract_field_names(value: list[str]) -> set[str]:
    names: set[str] = set()
    for item in value:
        token = str(item).strip()
        if not token:
            continue
        if ":" in token:
            token = token.split(":", 1)[0].strip()
        if token.endswith("(optional)"):
            token = token[: -len("(optional)")].strip()
        if token:
            names.add(token)
    return names


def _build_contract_from_legacy(spec: dict[str, Any]) -> RuntimePipelineContract:
    pipeline_id = str(spec.get("pipeline_id", "")).strip()
    if not pipeline_id:
        raise PipelineContractError("pipeline spec에 pipeline_id가 없다")

    nodes = _as_dicts(spec.get("nodes"), "nodes")
    if not nodes:
        raise PipelineContractError(f"pipeline {pipeline_id}의 nodes가 비어 있습니다")

    node_ids: list[str] = []
    for index, item in enumerate(nodes):
        node_id = str(item.get("node_id", "")).strip()
        if not node_id:
            raise PipelineContractError(f"pipeline {pipeline_id}의 노드[{index}]에 node_id가 없다")
        node_ids.append(node_id)
    if len(node_ids) != len(set(node_ids)):
        raise PipelineContractError(f"pipeline {pipeline_id}에 중복 node_id가 있다")

    runtime = _require_dict(spec.get("runtime", {}), "runtime")
    executor = str(runtime.get("executor", "")).strip()
    if not executor:
        raise PipelineContractError(
            f"pipeline spec {pipeline_id}의 runtime.executor가 필요합니다. "
            "예: workflow.pipelines.character_concept_art_generator:run_with_payload"
        )

    return RuntimePipelineContract(
        pipeline_id=pipeline_id,
        input_contract=_as_str_list(spec.get("input_contract", []), field_name="input_contract"),
        output_contract=_as_str_list(spec.get("output_contract", []), field_name="output_contract"),
        runtime_executor=executor,
        node_ids=node_ids,
        order=node_ids,
        node_contracts={},
        node_links=[],
    )


def _build_contract_from_new_format(spec: dict[str, Any]) -> RuntimePipelineContract:
    pipeline_id = str(spec.get("pipeline_id", "")).strip()
    if not pipeline_id:
        raise PipelineContractError("pipeline spec에 pipeline_id가 없다")

    runtime = _require_dict(spec.get("runtime", {}), "runtime")
    executor = str(runtime.get("executor", "")).strip()
    if not executor:
        raise PipelineContractError(
            f"pipeline spec {pipeline_id}의 runtime.executor가 필요합니다. "
            "예: workflow.pipelines.character_concept_art_generator:run_with_payload"
        )

    node_contract_list = _as_dicts(spec.get("node_contracts"), "node_contracts")
    if not node_contract_list:
        raise PipelineContractError(f"pipeline {pipeline_id}의 node_contracts가 비어 있습니다")

    nodes_in_file: list[dict[str, Any]] = []
    node_ids: list[str] = []
    for node in node_contract_list:
        node_id = str(node.get("node_id", "")).strip()
        if not node_id:
            raise PipelineContractError(f"pipeline {pipeline_id}의 node_contracts 항목에 node_id가 없다")
        node_ids.append(node_id)
        nodes_in_file.append(node)

    if len(node_ids) != len(set(node_ids)):
        raise PipelineContractError(f"pipeline {pipeline_id}에 중복 node_id가 있다")

    raw_order = spec.get("order")
    order = _as_str_list(raw_order, field_name="order")
    if not order:
        order_pairs: list[tuple[int, int, str]] = []
        for index, node in enumerate(nodes_in_file):
            pos = node.get("position", index)
            try:
                position = int(pos)
            except (TypeError, ValueError) as exc:
                raise PipelineContractError(
                    f"pipeline {pipeline_id}의 node_contracts[{node.get('node_id')}] position이 정수가 아닙니다"
                ) from exc
            order_pairs.append((position, index, str(node["node_id"])) )
        order = [node_id for _, _, node_id in sorted(order_pairs)]
    else:
        if len(order) != len(set(order)):
            raise PipelineContractError(f"pipeline {pipeline_id}의 order가 중복됩니다")

    if set(order) != set(node_ids):
        missing = sorted(set(node_ids) - set(order))
        extra = sorted(set(order) - set(node_ids))
        if missing:
            raise PipelineContractError(
                f"pipeline {pipeline_id}의 order에 누락된 node_id가 있습니다: {missing}"
            )
        if extra:
            raise PipelineContractError(
                f"pipeline {pipeline_id}의 order에 정의되지 않은 node_id가 있습니다: {extra}"
            )

    node_contracts: dict[str, dict[str, Any]] = {}
    node_outputs: dict[str, set[str]] = {}

    for index, node_id in enumerate(node_ids):
        node = _require_dict(nodes_in_file[index], f"node_contracts[{node_id}]")
        node_contracts[node_id] = node
        inputs = _as_dicts(node.get("inputs"), f"{node_id}.inputs")
        outputs = _as_dicts(node.get("outputs"), f"{node_id}.outputs")

        if not outputs:
            raise PipelineContractError(f"{node_id}.outputs는 최소 1개 이상이어야 합니다")

        input_names: list[str] = []
        for item in inputs:
            name = str(item.get("name", "")).strip()
            if not name:
                raise PipelineContractError(f"{node_id}.inputs에 name 필드가 필요합니다")
            source = str(item.get("source", "")).strip()
            if not source:
                raise PipelineContractError(f"{node_id}.{name}.source가 필요합니다")
            if source == "pipeline.input":
                pass
            elif source not in node_ids:
                raise PipelineContractError(f"{node_id}.{name}.source에 알 수 없는 노드가 있습니다: {source}")
            input_names.append(name)
        if len(input_names) != len(set(input_names)):
            raise PipelineContractError(f"{node_id}.inputs.name은 중복될 수 없습니다")

        output_names: list[str] = []
        for item in outputs:
            name = str(item.get("name", "")).strip()
            if not name:
                raise PipelineContractError(f"{node_id}.outputs에 name 필드가 필요합니다")
            output_names.append(name)
        if len(output_names) != len(set(output_names)):
            raise PipelineContractError(f"{node_id}.outputs.name은 중복될 수 없습니다")

        node_outputs[node_id] = set(output_names)

    links = _as_dicts(spec.get("node_links"), "node_links")
    link_inputs_by_target: dict[str, list[tuple[str, str]]] = {}
    for item in links:
        source = str(item.get("from", "")).strip()
        target = str(item.get("to", "")).strip()
        if not source or not target:
            raise PipelineContractError("node_links 항목에 from/to가 필요합니다")
        if target not in node_ids:
            raise PipelineContractError(f"node_links.to에 알 수 없는 노드가 있습니다: {target}")
        if source not in {"pipeline.input"} | set(node_ids):
            raise PipelineContractError(f"node_links.from에 알 수 없는 노드가 있습니다: {source}")
        mapping = _as_str_dict(item.get("mapping"), f"node_links[{source}->{target}].mapping")

        if source == "pipeline.input":
            defined_input_fields = _parse_contract_field_names(
                _as_str_list(spec.get("input_contract", []), field_name="input_contract")
            )
            for input_name in mapping.values():
                if input_name not in defined_input_fields:
                    raise PipelineContractError(
                        f"node_links[{source}->{target}]의 {input_name}은 input_contract에 없어야 전달할 수 없습니다"
                    )
        else:
            missing_outputs = [src_field for src_field in mapping.keys() if src_field not in node_outputs.get(source, set())]
            if missing_outputs:
                raise PipelineContractError(
                    f"node_links[{source}->{target}] 의 출력 필드가 존재하지 않습니다: {missing_outputs}"
                )

        for src_field, dst_field in mapping.items():
            link_inputs_by_target.setdefault(target, []).append((f"{source}.{src_field}", dst_field))

    input_contract_fields = _parse_contract_field_names(
        _as_str_list(spec.get("input_contract", []), field_name="input_contract")
    )
    order_index = {node_id: index for index, node_id in enumerate(order)}
    for node_id in node_ids:
        if node_id not in order_index:
            raise PipelineContractError(f"{node_id}가 order에 없습니다")
        for item in _as_dicts(node_contracts[node_id].get("inputs"), f"{node_id}.inputs"):
            name = str(item.get("name", "")).strip()
            source = str(item.get("source", "")).strip()
            required = bool(item.get("required", True))
            if source == "pipeline.input":
                if required and name not in input_contract_fields:
                    raise PipelineContractError(
                        f"{node_id}.{name} required 입력은 input_contract에 존재해야 합니다"
                    )
                continue

            if not required:
                continue

            candidates = [
                tuple(pair.split(".", 1))
                for pair in [entry[0] for entry in link_inputs_by_target.get(node_id, []) if entry[1] == name]
                if "." in pair
            ]
            if not candidates:
                raise PipelineContractError(
                    f"{node_id}.{name} required 입력의 전달 경로가 node_links에 없습니다"
                )
            for source_node, source_field in candidates:
                if source_node == "pipeline.input":
                    continue
                if order_index[source_node] >= order_index[node_id]:
                    raise PipelineContractError(
                        f"node_links 순서 위반: {source_node} -> {node_id}"
                    )

    return RuntimePipelineContract(
        pipeline_id=pipeline_id,
        input_contract=_as_str_list(spec.get("input_contract", []), field_name="input_contract"),
        output_contract=_as_str_list(spec.get("output_contract", []), field_name="output_contract"),
        runtime_executor=executor,
        node_ids=node_ids,
        order=order,
        node_contracts=node_contracts,
        node_links=links,
    )


def parse_pipeline_contract(spec: dict[str, Any]) -> RuntimePipelineContract:
    """현재 스펙 포맷을 판별해 런타임 계약 객체로 변환한다."""
    if not isinstance(spec, dict):
        raise PipelineContractError("pipeline spec은 객체(JSON)여야 합니다")

    if "node_contracts" in spec:
        return _build_contract_from_new_format(spec)
    return _build_contract_from_legacy(spec)
