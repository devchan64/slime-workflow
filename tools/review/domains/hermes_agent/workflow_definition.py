"""워크플로우 단계의 필수 입력과 출력 연결을 접수 전에 검증한다."""
from graphlib import CycleError, TopologicalSorter


def validate_fixed_workflow_input(current_field_name, current_field_contract, current_input_value):
    current_input_kind = current_field_contract["type"]
    if current_input_kind == "text":
        valid_input_value = (isinstance(current_input_value, str) and bool(current_input_value.strip())
                             and len(current_input_value) <= current_field_contract.get("max_length", len(current_input_value)))
    elif current_input_kind == "integer":
        valid_input_value = (type(current_input_value) is int
                             and current_field_contract.get("min", current_input_value) <= current_input_value
                             <= current_field_contract.get("max", current_input_value)
                             and current_input_value % current_field_contract.get("step", 1) == 0)
    elif current_input_kind == "png_list":
        from tools.review.domains.image.three_reference_generation import decode_reference_image
        valid_input_value = isinstance(current_input_value, list) and len(current_input_value) <= current_field_contract["max_items"]
        if valid_input_value:
            for current_image_text in current_input_value:
                decode_reference_image(current_image_text)
    elif current_input_kind == "glossary":
        from tools.review.domains.translation.service import validate_translation_glossary
        validate_translation_glossary(current_input_value)
        valid_input_value = True
    else:
        raise ValueError("등록되지 않은 입력 유형입니다.")
    if not valid_input_value or ("choices" in current_field_contract and current_input_value not in current_field_contract["choices"]):
        raise ValueError(f"입력 형식 또는 허용 범위를 확인하세요: {current_field_name}")


def compile_workflow_dependencies(workflow_step_records, generator_contract_records):
    """계약의 inputs는 필드별 type/required, outputs는 출력별 type을 담는다."""
    if not isinstance(workflow_step_records, list):
        raise ValueError("단계 목록이 필요합니다.")
    workflow_step_lookup = {}
    for current_step_record in workflow_step_records:
        if (not isinstance(current_step_record, dict) or not {"id", "generator"} <= current_step_record.keys()
                or current_step_record.keys() - {"id", "generator", "generator_version", "template_version", "inputs", "bindings"}
                or not isinstance(current_step_record["generator"], str)):
            raise ValueError("단계 정의 필드를 확인하세요.")
        current_step_identifier = current_step_record["id"]
        if not isinstance(current_step_identifier, str) or not current_step_identifier.strip():
            raise ValueError("단계 ID가 필요합니다.")
        if current_step_identifier in workflow_step_lookup:
            raise ValueError("단계 ID가 중복되었습니다.")
        if current_step_record["generator"] not in generator_contract_records:
            raise ValueError("등록되지 않은 생성기입니다.")
        current_generator_contract = generator_contract_records[current_step_record["generator"]]
        for step_version_field, catalog_version_field in (("generator_version", "version"), ("template_version", "template_version")):
            if step_version_field in current_step_record:
                reviewed_version_value = current_step_record[step_version_field]
                if type(reviewed_version_value) is not int or reviewed_version_value != current_generator_contract[catalog_version_field]:
                    raise ValueError(f"{current_step_identifier} 단계의 생성기 또는 템플릿 버전이 변경됐습니다. 다시 검토하세요.")
        workflow_step_lookup[current_step_identifier] = current_step_record
    if not workflow_step_lookup:
        raise ValueError("실행할 단계가 필요합니다.")

    workflow_dependency_records = {}
    for current_step_identifier, current_step_record in workflow_step_lookup.items():
        current_input_contracts = generator_contract_records[current_step_record["generator"]]["inputs"]
        fixed_input_values = current_step_record.get("inputs", {})
        bound_input_values = current_step_record.get("bindings", {})
        if not isinstance(fixed_input_values, dict) or not isinstance(bound_input_values, dict):
            raise ValueError("입력과 연결은 객체여야 합니다.")
        supplied_field_names = fixed_input_values.keys() | bound_input_values.keys()
        if fixed_input_values.keys() & bound_input_values.keys() or supplied_field_names - current_input_contracts.keys():
            raise ValueError("입력 필드가 중복되거나 등록되지 않았습니다.")
        for current_field_name, current_field_contract in current_input_contracts.items():
            if current_field_contract["required"] and current_field_name not in supplied_field_names:
                raise ValueError(f"필수 입력 누락: {current_step_identifier}.{current_field_name}")
        for current_field_name, current_input_value in fixed_input_values.items():
            validate_fixed_workflow_input(current_field_name, current_input_contracts[current_field_name], current_input_value)
        source_step_identifiers = set()
        for current_field_name, current_binding_record in bound_input_values.items():
            if (not isinstance(current_binding_record, dict) or set(current_binding_record) not in ({"from_step", "output"}, {"from_step", "output", "selection"})
                    or current_binding_record.get("selection", "user_choice") != "user_choice"
                    or not all(isinstance(value, str) for value in current_binding_record.values())):
                raise ValueError("지원하지 않는 출력 연결 형식입니다.")
            source_step_identifier = current_binding_record["from_step"]
            if source_step_identifier not in workflow_step_lookup:
                raise ValueError("연결한 생산 단계가 없습니다.")
            source_generator_name = workflow_step_lookup[source_step_identifier]["generator"]
            source_output_contracts = generator_contract_records[source_generator_name]["outputs"]
            source_output_name = current_binding_record["output"]
            if source_output_name not in source_output_contracts:
                raise ValueError("생성기에 등록된 출력이 아닙니다.")
            if source_output_contracts[source_output_name]["type"] != current_input_contracts[current_field_name]["type"]:
                raise ValueError("생성 결과와 입력의 형식이 다릅니다.")
            source_step_identifiers.add(source_step_identifier)
        workflow_dependency_records[current_step_identifier] = tuple(sorted(source_step_identifiers))
    try:
        tuple(TopologicalSorter(workflow_dependency_records).static_order())
    except CycleError as detected_cycle_error:
        raise ValueError("단계 연결에 순환이 있습니다.") from detected_cycle_error
    return workflow_dependency_records
