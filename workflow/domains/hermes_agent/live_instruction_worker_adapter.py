"""Connect a managed-worker agent to its own job-scoped control socket."""
import json
import os
from pathlib import Path
import socket
import sys
import threading

from live_instruction_runtime import LiveInstructionRuntime
from live_instruction_launcher import serve

CONTROL = Path('/control/live')
SOCKET = CONTROL / 'agent.sock'
RECEIPT = CONTROL / 'settled.json'


def install_on_agent_class(agent_class):
    original_init = agent_class.__init__
    def init(agent, *args, **kwargs):
        original_init(agent, *args, **kwargs)
        try:
            install_on_agent(agent)
        except (AttributeError, OSError, TypeError) as error:
            print('실행 중 지시 제어 준비 실패:', type(error).__name__, str(error)[:160], file=sys.stderr, flush=True)
    agent_class.__init__ = init


def install_on_agent(agent):
    runtime = LiveInstructionRuntime(agent)
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        listener.bind(str(SOCKET))
        os.chmod(SOCKET, 0o600)
        listener.listen(4)
    except OSError:
        listener.close()
        raise
    receipt_lock = threading.Lock()
    def write_receipts(rows):
        try:
            with receipt_lock:
                temporary = RECEIPT.with_suffix('.tmp')
                temporary.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
                os.replace(temporary, RECEIPT)
        except OSError:
            pass
    persist = agent._persist_session
    def wrapped_persist(messages, *args, **kwargs):
        value = persist(messages, *args, **kwargs)
        rows = runtime.observe(messages)
        if rows:
            write_receipts(rows)
        return value
    run = agent.run_conversation
    def wrapped_run(*args, **kwargs):
        result = None
        try:
            result = run(*args, **kwargs)
            if isinstance(result, dict):
                runtime.observe(result.get('messages', []))
            return result
        finally:
            listener.close()
            write_receipts(runtime.close(result))
    agent._persist_session = wrapped_persist
    agent.run_conversation = wrapped_run
    threading.Thread(target=serve, args=(runtime, listener), daemon=True).start()
