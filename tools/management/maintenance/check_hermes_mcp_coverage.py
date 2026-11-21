"""MCP 도구의 고정 명령과 Hermes 기능 목록의 인터페이스 표기를 대조한다."""
import ast
from pathlib import Path
import sys

from tools.management.domains.hermes_agent.capabilities import list_hermes_capability_catalog

HERMES_MCP_DISPATCH_NAMES=frozenset({'run_hermes_mcp_command','execute_hermes_cancellation_command'})


def inspect_hermes_mcp_command_coverage(current_source_text,current_capability_records):
    """등록 장식자가 있는 도구의 고정 명령만 확인하며 실행 성공은 검증하지 않는다."""
    current_source_tree=ast.parse(current_source_text)
    current_command_names=set()
    current_dynamic_tools=[]
    current_unsafe_read_tools=[]
    current_contract_map={current_record['command']:current_record for current_record in current_capability_records}
    for current_function_node in current_source_tree.body:
        if not isinstance(current_function_node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
        if not any(isinstance(current_decorator,ast.Call) and isinstance(current_decorator.func,ast.Attribute) and isinstance(current_decorator.func.value,ast.Name) and current_decorator.func.value.id=='hermes_mcp_server' and current_decorator.func.attr=='tool' for current_decorator in current_function_node.decorator_list):continue
        current_read_only_value=False
        for current_decorator in current_function_node.decorator_list:
            if not isinstance(current_decorator,ast.Call) or not isinstance(current_decorator.func,ast.Attribute) or not isinstance(current_decorator.func.value,ast.Name) or current_decorator.func.value.id!='hermes_mcp_server' or current_decorator.func.attr!='tool':continue
            for current_keyword in current_decorator.keywords:
                if current_keyword.arg!='annotations' or not isinstance(current_keyword.value,ast.Call) or not isinstance(current_keyword.value.func,ast.Name) or current_keyword.value.func.id!='ToolAnnotations':continue
                current_read_only_value=any(current_option.arg=='read_only_hint' and isinstance(current_option.value,ast.Constant) and current_option.value.value is True for current_option in current_keyword.value.keywords)
        for current_call_node in ast.walk(current_function_node):
            if not isinstance(current_call_node,ast.Call) or not isinstance(current_call_node.func,ast.Name) or current_call_node.func.id not in HERMES_MCP_DISPATCH_NAMES:continue
            if not current_call_node.args or not isinstance(current_call_node.args[0],ast.Constant) or not isinstance(current_call_node.args[0].value,str):
                current_dynamic_tools.append(current_function_node.name)
            else:
                current_command_name=current_call_node.args[0].value
                current_command_names.add(current_command_name)
                current_contract_value=current_contract_map.get(current_command_name)
                if current_read_only_value and current_contract_value is not None and current_contract_value.get('effect')!='read':current_unsafe_read_tools.append(current_function_node.name)
    current_advertised_names={current_capability['command'] for current_capability in current_capability_records if 'mcp' in current_capability['interfaces']}
    return {'advertised':len(current_advertised_names),'dispatched':len(current_command_names),'missing':sorted(current_advertised_names-current_command_names),'unadvertised':sorted(current_command_names-current_advertised_names),'dynamic':sorted(set(current_dynamic_tools)),'unsafe_read_only':sorted(set(current_unsafe_read_tools))}


def inspect_hermes_mcp_only_coverage(current_source_text,current_only_records):
    """게이트웨이 명령 호출이 없는 MCP 전용 도구의 이름과 읽기 표기를 대조한다."""
    current_source_tree=ast.parse(current_source_text)
    current_only_tools={}
    for current_function_node in current_source_tree.body:
        if not isinstance(current_function_node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
        current_tool_decorators=[current_decorator for current_decorator in current_function_node.decorator_list if isinstance(current_decorator,ast.Call) and isinstance(current_decorator.func,ast.Attribute) and isinstance(current_decorator.func.value,ast.Name) and current_decorator.func.value.id=='hermes_mcp_server' and current_decorator.func.attr=='tool']
        if not current_tool_decorators:continue
        if any(isinstance(current_call_node,ast.Call) and isinstance(current_call_node.func,ast.Name) and current_call_node.func.id in HERMES_MCP_DISPATCH_NAMES for current_call_node in ast.walk(current_function_node)):continue
        current_read_only=any(current_keyword.arg=='annotations' and isinstance(current_keyword.value,ast.Call) and any(current_option.arg=='read_only_hint' and isinstance(current_option.value,ast.Constant) and current_option.value.value is True for current_option in current_keyword.value.keywords) for current_decorator in current_tool_decorators for current_keyword in current_decorator.keywords)
        current_positional_arguments=current_function_node.args.posonlyargs+current_function_node.args.args
        current_required_count=len(current_positional_arguments)-len(current_function_node.args.defaults)
        current_required_names=[current_argument.arg for current_argument in current_positional_arguments[:current_required_count]]+[current_argument.arg for current_argument,current_default in zip(current_function_node.args.kwonlyargs,current_function_node.args.kw_defaults) if current_default is None]
        current_optional_names=[current_argument.arg for current_argument in current_positional_arguments[current_required_count:]]+[current_argument.arg for current_argument,current_default in zip(current_function_node.args.kwonlyargs,current_function_node.args.kw_defaults) if current_default is not None]
        current_only_tools[current_function_node.name]={'read_only':current_read_only,'required':current_required_names,'optional':current_optional_names,'variadic':bool(current_function_node.args.vararg or current_function_node.args.kwarg)}
    current_record_names=[current_record['name'] for current_record in current_only_records]
    current_duplicate_names=sorted({current_name_value for current_name_value in current_record_names if current_record_names.count(current_name_value)>1})
    current_contract_names=set(current_record_names)
    current_unsafe_names=sorted({current_record['name'] for current_record in current_only_records if current_only_tools.get(current_record['name'],{}).get('read_only') and current_record.get('effect')!='read'})
    current_input_mismatch=sorted({current_record['name'] for current_record in current_only_records if current_record['name'] in current_only_tools and (current_only_tools[current_record['name']]['variadic'] or current_record.get('required')!=current_only_tools[current_record['name']]['required'] or current_record.get('optional')!=current_only_tools[current_record['name']]['optional'])})
    return {'missing':sorted(set(current_only_tools)-current_contract_names),'unregistered':sorted(current_contract_names-set(current_only_tools)),'duplicate':current_duplicate_names,'unsafe_read_only':current_unsafe_names,'input_mismatch':current_input_mismatch}


def run_hermes_mcp_coverage_check():
    current_mcp_source=Path(__file__).resolve().parents[1]/'domains/hermes_agent/mcp_server.py'
    current_source_text=current_mcp_source.read_text(encoding='utf-8')
    current_catalog_value=list_hermes_capability_catalog()
    current_result_value=inspect_hermes_mcp_command_coverage(current_source_text,current_catalog_value['records'])
    current_only_result=inspect_hermes_mcp_only_coverage(current_source_text,current_catalog_value['mcp_only_tools'])
    print('MCP 표기 {advertised}개 · 도구의 고정 명령 {dispatched}개'.format(**current_result_value))
    for current_issue_name in ('missing','unadvertised','dynamic','unsafe_read_only'):
        for current_issue_value in current_result_value[current_issue_name]:print(current_issue_name+': '+current_issue_value)
    for current_issue_name,current_issue_values in current_only_result.items():
        for current_issue_value in current_issue_values:print('mcp_only_'+current_issue_name+': '+current_issue_value)
    return 1 if any(current_result_value[current_issue_name] for current_issue_name in ('missing','unadvertised','dynamic','unsafe_read_only')) or any(current_only_result.values()) else 0


if __name__=='__main__':
    sys.exit(run_hermes_mcp_coverage_check())
