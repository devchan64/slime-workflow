"""Install the job-local adapter only in Hermes' managed-worker interpreter.

The hook delays importing run_agent until Hermes loads it after freezing policy.
"""
import importlib.abc
import importlib.machinery
import os
import sys


def is_managed_worker(argv):
    return any(value == '-m' and index + 1 < len(argv) and argv[index + 1] == 'agent.managed_worker'
               for index, value in enumerate(argv))


class AgentLoader(importlib.abc.Loader):
    def __init__(self, delegate):
        self.delegate = delegate

    def create_module(self, spec):
        method = getattr(self.delegate, 'create_module', None)
        return method(spec) if method else None

    def exec_module(self, module):
        self.delegate.exec_module(module)
        from live_instruction_worker_adapter import install_on_agent_class
        install_on_agent_class(module.AIAgent)


class AgentFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname != 'run_agent':
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec and spec.loader:
            spec.loader = AgentLoader(spec.loader)
        return spec


if is_managed_worker(getattr(sys, 'orig_argv', [])) and os.path.isdir('/control/live'):
    sys.meta_path.insert(0, AgentFinder())
