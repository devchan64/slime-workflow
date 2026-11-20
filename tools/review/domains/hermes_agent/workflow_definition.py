"""워크플로우 단계의 필수 입력과 출력 연결을 접수 전에 검증한다."""
from graphlib import CycleError, TopologicalSorter


def compile_workflow_dependencies(workflow_step_records, generator_contract_records):
    """계약의 inputs는 필드별 type/required, outputs는 출력별 type을 담는다."""
    workflow_step_lookup = {}
    for current_step_record in workflow_step_records:
        current_step_identifier = current_step_record["id"]
        if not isinstance(current_step_identifier, str) or not current_step_identifier.strip():
            raise ValueError("단계 ID가 필요합니다.")
        if current_step_identifier in workflow_step_lookup:
            raise ValueError("단계 ID가 중복되었습니다.")
        if current_step_record["generator"] not in generator_contract_records:
            raise ValueError("등록되지 않은 생성기입니다.")
        workflow_step_lookup[current_step_identifier] = current_step_record
    if not workflow_step_lookup:
        raise ValueError("실행할 단계가 필요합니다.")

    workflow_dependency_records = {}
    for current_step_identifier, current_step_record in workflow_step_lookup.items():
        current_input_contracts = generator_contract_records[current_step_record["generator"]]["inputs"]
        fixed_input_values = current_step_record.get("inputs", {})
        bound_input_values = current_step_record.get("bindings", {})
        supplied_field_names = fixed_input_values.keys() | bound_input_values.keys()
        if fixed_input_values.keys() & bound_input_values.keys() or supplied_field_names - current_input_contracts.keys():
            raise ValueError("입력 필드가 중복되거나 등록되지 않았습니다.")
        for current_field_name, current_field_contract in current_input_contracts.items():
            if current_field_contract["required"] and current_field_name not in supplied_field_names:
                raise ValueError(f"필수 입력 누락: {current_step_identifier}.{current_field_name}")
        source_step_identifiers = set()
        for current_field_name, current_binding_record in bound_input_values.items():
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
