"""MCP 도구의 고정 명령과 Hermes 기능 목록의 인터페이스 표기를 대조한다."""
import ast
from pathlib import Path
import sys

from tools.review.domains.hermes_agent.capabilities import list_hermes_capability_catalog

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


def run_hermes_mcp_coverage_check():
    current_mcp_source=Path(__file__).resolve().parents[1]/'domains/hermes_agent/mcp_server.py'
    current_result_value=inspect_hermes_mcp_command_coverage(current_mcp_source.read_text(encoding='utf-8'),list_hermes_capability_catalog()['records'])
    print('MCP 표기 {advertised}개 · 도구의 고정 명령 {dispatched}개'.format(**current_result_value))
    for current_issue_name in ('missing','unadvertised','dynamic','unsafe_read_only'):
        for current_issue_value in current_result_value[current_issue_name]:print(current_issue_name+': '+current_issue_value)
    return 1 if any(current_result_value[current_issue_name] for current_issue_name in ('missing','unadvertised','dynamic','unsafe_read_only')) else 0


if __name__=='__main__':
    sys.exit(run_hermes_mcp_coverage_check())
