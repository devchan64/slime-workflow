"""대화에서 작성한 워크플로우 정의를 검토하고 실행 입력을 고정한다."""
import re
import uuid


def review_conversation_workflow_definition(current_session_identifier, workflow_definition_text):
    from workflow.common.management_gateway import parse_management_request_json
    from workflow.domains.hermes_agent.workflow_catalog import create_workflow_step_draft, read_workflow_generator_catalog
    from workflow.domains.hermes_agent.workflow_definition import compile_workflow_dependencies
    if not re.fullmatch(r"[a-f0-9]{32}", current_session_identifier or ""):
        raise ValueError("대화 세션을 선택하세요.")
    current_proposal_record = parse_management_request_json(workflow_definition_text)
    if not isinstance(current_proposal_record, dict) or set(current_proposal_record) != {"steps"} or not isinstance(current_proposal_record["steps"], list):
        raise ValueError("steps 목록을 확인하세요.")
    current_generator_catalog = read_workflow_generator_catalog()
    normalized_step_records = []
    step_input_sources = {}
    for step_position_number, current_step_record in enumerate(current_proposal_record["steps"], start=1):
        if not isinstance(current_step_record, dict) or set(current_step_record) - {"id", "generator", "generator_version", "template_version", "inputs", "bindings"}:
            raise ValueError(f"{step_position_number}번째 단계의 정의를 확인하세요.")
        current_step_identifier = current_step_record.get("id")
        current_generator_name = current_step_record.get("generator")
        if not isinstance(current_step_identifier, str) or not current_step_identifier.strip():
            raise ValueError(f"{step_position_number}번째 단계의 id에 이름을 입력하세요.")
        if not isinstance(current_generator_name, str) or current_generator_name not in current_generator_catalog:
            raise ValueError(f"{step_position_number}번째 단계의 generator에서 등록된 생성기를 선택하세요.")
        fixed_input_record = current_step_record.get("inputs", {})
        bound_input_record = current_step_record.get("bindings", {})
        if not isinstance(fixed_input_record, dict) or not isinstance(bound_input_record, dict):
            raise ValueError(f"{current_step_identifier} 단계의 inputs와 bindings를 객체로 작성하세요.")
        duplicate_input_fields = fixed_input_record.keys() & bound_input_record.keys()
        if duplicate_input_fields:
            duplicate_field_names = ", ".join(sorted(duplicate_input_fields))
            raise ValueError(f"{current_step_identifier} 단계의 {duplicate_field_names}에 값과 연결이 함께 있습니다. "
                           "선행 결과를 사용하려면 inputs에서 해당 필드를 지우세요.")
        for input_field_name, input_field_contract in current_generator_catalog[current_generator_name]["inputs"].items():
            if (input_field_contract["required"] and input_field_name not in bound_input_record
                    and fixed_input_record.get(input_field_name, input_field_contract.get("default")) is None):
                raise ValueError(f"{current_step_identifier} 단계의 inputs.{input_field_name} 값을 입력하세요. "
                               f"선행 결과를 사용하려면 inputs에서 필드를 지우고 bindings.{input_field_name}에 연결하세요.")
        normalized_step_record = create_workflow_step_draft(current_step_identifier, current_generator_name, fixed_input_record)
        for reviewed_version_field in ("generator_version", "template_version"):
            if reviewed_version_field in current_step_record:
                normalized_step_record[reviewed_version_field] = current_step_record[reviewed_version_field]
        for current_field_name in bound_input_record:
            normalized_step_record["inputs"].pop(current_field_name, None)
        normalized_step_record["bindings"] = bound_input_record
        normalized_step_records.append(normalized_step_record)
        current_input_sources = {}
        for input_field_name, current_input_value in normalized_step_record["inputs"].items():
            input_field_contract = current_generator_catalog[current_generator_name]["inputs"][input_field_name]
            if input_field_name not in fixed_input_record:
                input_source_label = "생성기 기본값"
            elif "default" in input_field_contract and current_input_value == input_field_contract["default"]:
                input_source_label = "초안에 포함된 생성기 기본값"
            else:
                input_source_label = "초안 지정값"
            current_input_sources[input_field_name] = input_source_label
        current_input_sources.update(dict.fromkeys(bound_input_record, "선행 단계 결과"))
        step_input_sources[current_step_identifier] = current_input_sources
    compile_workflow_dependencies(normalized_step_records, current_generator_catalog)
    return {"session_id": current_session_identifier, "run_id": uuid.uuid4().hex, "steps": normalized_step_records,
            "input_sources": step_input_sources}


def extract_conversation_workflow_proposal(current_answer_text):
    if "HERMES_WORKFLOW_PROPOSAL" not in current_answer_text:
        fenced_json_blocks = re.findall(r"(?ms)^```json[ \t]*\n(.*?)\n```[ \t]*$", current_answer_text)
        if len(fenced_json_blocks) == 1:
            from workflow.common.management_gateway import parse_management_request_json
            proposal_definition = parse_management_request_json(fenced_json_blocks[0])
            if isinstance(proposal_definition, dict) and set(proposal_definition) == {"steps"} and isinstance(proposal_definition["steps"], list):
                return fenced_json_blocks[0]
    proposal_block_values = re.findall(r"(?ms)^HERMES_WORKFLOW_PROPOSAL[ \t]*\n(.*?)\nEND_HERMES_WORKFLOW_PROPOSAL[ \t]*$", current_answer_text)
    if len(proposal_block_values) != 1:
        raise ValueError("선택한 답변에서 워크플로우 제안 한 개를 확인하세요.")
    return proposal_block_values[0]
