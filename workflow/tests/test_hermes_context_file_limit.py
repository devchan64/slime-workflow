import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from workflow.domains.hermes_agent.sandbox_client import configure_sandbox_home

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / '.local/hermes-agent-runtime'


class ContextFileLimitTests(unittest.TestCase):
    def test_isolated_runtime_loads_full_agents_file_with_bypass_enabled(self):
        python = RUNTIME / '.venv/bin/python'
        if not python.is_file():
            self.skipTest('Hermes 런타임이 없습니다.')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / 'home'
            workspace = root / 'workspace'
            workspace.mkdir()
            configure_sandbox_home(home)
            content = 'A' * 15000 + 'MIDDLE_RULE_MARKER' + 'Z' * 15000
            (workspace / 'AGENTS.md').write_text(content, encoding='utf-8')
            env = dict(os.environ, HERMES_HOME=str(home), HERMES_IGNORE_USER_CONFIG='1', PYTHONPATH=str(RUNTIME))
            script = ('from agent.prompt_builder import _get_context_file_max_chars, _load_agents_md; '
                      'import sys; from pathlib import Path; s = _load_agents_md(Path(sys.argv[1])); '
                      'print(_get_context_file_max_chars()); print("MIDDLE_RULE_MARKER" in s); '
                      'print("TRUNCATED" in s)')
            result = subprocess.run([str(python), '-c', script, str(workspace)], env=env, capture_output=True, text=True, timeout=30, check=True)
            self.assertEqual(result.stdout.splitlines(), ['40000', 'True', 'False'])


if __name__ == '__main__':
    unittest.main()
