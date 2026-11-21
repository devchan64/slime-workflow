import unittest

from tools.management.maintenance.check_hermes_mcp_coverage import inspect_hermes_mcp_command_coverage


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

    def test_mcp_only_coverage_detects_missing_duplicates_and_read_only_mismatch(self):
        from tools.management.maintenance.check_hermes_mcp_coverage import inspect_hermes_mcp_only_coverage
        current_source_text='''
@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True))
def direct_tool():
    return fetch_health()
@hermes_mcp_server.tool()
def hidden_tool():
    return fetch_queue()
@hermes_mcp_server.tool()
def gateway_tool():
    return run_hermes_mcp_command('hermes-status', {})
'''
        current_only_records=[{'name':'direct_tool','effect':'write'},{'name':'direct_tool','effect':'write'},{'name':'obsolete_tool','effect':'read'}]
        current_result_value=inspect_hermes_mcp_only_coverage(current_source_text,current_only_records)
        self.assertEqual(current_result_value['missing'],['hidden_tool'])
        self.assertEqual(current_result_value['unregistered'],['obsolete_tool'])
        self.assertEqual(current_result_value['duplicate'],['direct_tool'])
        self.assertIn('direct_tool',current_result_value['unsafe_read_only'])
        self.assertEqual(current_result_value['input_mismatch'],['direct_tool'])

    def test_mcp_only_coverage_checks_required_optional_and_variadic_inputs(self):
        from tools.management.maintenance.check_hermes_mcp_coverage import inspect_hermes_mcp_only_coverage
        current_source_text='''
@hermes_mcp_server.tool()
def fixed_tool(required_value, optional_value=1, *, required_flag, optional_flag=False):
    return fetch_value()
@hermes_mcp_server.tool()
def variable_tool(*args):
    return fetch_value()
'''
        current_records=[{'name':'fixed_tool','effect':'read','required':['required_value','required_flag'],'optional':['optional_value','optional_flag']},{'name':'variable_tool','effect':'read','required':[],'optional':[]}]
        current_result_value=inspect_hermes_mcp_only_coverage(current_source_text,current_records)
        self.assertEqual(current_result_value['input_mismatch'],['variable_tool'])
