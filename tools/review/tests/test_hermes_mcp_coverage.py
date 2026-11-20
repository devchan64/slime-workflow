import unittest

from tools.review.maintenance.check_hermes_mcp_coverage import inspect_hermes_mcp_command_coverage


class HermesMcpCoverageTests(unittest.TestCase):
    def test_reports_missing_unadvertised_and_dynamic_dispatch(self):
        current_source_text='''
@hermes_mcp_server.tool()
def regular_tool():
    return run_hermes_mcp_command('hermes-valid', {})
@hermes_mcp_server.tool()
def cancel_tool():
    return execute_hermes_cancellation_command('hermes-cancel', {})
@hermes_mcp_server.tool()
def extra_tool():
    return run_hermes_mcp_command('hermes-extra', {})
@hermes_mcp_server.tool()
def dynamic_tool(current_name):
    return run_hermes_mcp_command(current_name, {})
def unregistered_helper():
    return run_hermes_mcp_command('hermes-missing', {})
'''
        current_capability_records=[{'command':current_name,'interfaces':['mcp']} for current_name in ('hermes-valid','hermes-cancel','hermes-missing')]
        current_result_value=inspect_hermes_mcp_command_coverage(current_source_text,current_capability_records)
        self.assertEqual(current_result_value['missing'],['hermes-missing'])
        self.assertEqual(current_result_value['unadvertised'],['hermes-extra'])
        self.assertEqual(current_result_value['dynamic'],['dynamic_tool'])
        self.assertEqual(current_result_value['advertised'],3)
        self.assertEqual(current_result_value['dispatched'],3)

    def test_ignores_non_mcp_capability_and_foreign_decorator(self):
        current_source_text='''
@other_server.tool()
def foreign_tool():
    return run_hermes_mcp_command('hermes-local', {})
'''
        current_result_value=inspect_hermes_mcp_command_coverage(current_source_text,[{'command':'hermes-local','interfaces':['gui']}])
        self.assertEqual(current_result_value['missing'],[])
        self.assertEqual(current_result_value['unadvertised'],[])
        self.assertEqual(current_result_value['dynamic'],[])

    def test_read_only_hint_rejects_writes_and_bookkeeping(self):
        current_source_text="""
@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True))
def unsafe_write_tool():
    return run_hermes_mcp_command('hermes-write', {})
@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True))
def unsafe_lock_tool():
    return run_hermes_mcp_command('hermes-lock', {})
@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True))
def proper_read_tool():
    return run_hermes_mcp_command('hermes-read', {})
@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False))
def proper_write_tool():
    return run_hermes_mcp_command('hermes-write', {})
"""
        current_capability_records=[{'command':current_name,'interfaces':['mcp'],'effect':current_effect} for current_name,current_effect in (('hermes-write','write'),('hermes-lock','local_bookkeeping'),('hermes-read','read'))]
        current_result_value=inspect_hermes_mcp_command_coverage(current_source_text,current_capability_records)
        self.assertEqual(current_result_value['unsafe_read_only'],['unsafe_lock_tool','unsafe_write_tool'])
