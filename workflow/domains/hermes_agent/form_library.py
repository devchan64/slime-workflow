"""대화 세션의 폼 목록과 불변 입력 버전을 관리한다."""
import fcntl
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile


def replace_private_file(path, content):
    with NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        try:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)


def execute_form_library(directory, command, payload):
    session = payload["session_id"]
    if not isinstance(session, str) or not re.fullmatch("[a-f0-9]{32}", session):
        raise ValueError("대화 세션을 선택하세요.")
    folder = directory / "forms" / session
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    index = folder / "index.json"
    with (folder / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX if command == "save" else fcntl.LOCK_SH)
        library = json.loads(index.read_bytes()) if index.exists() else {"schema_version": 1, "session_id": session, "forms": {}}
        if library.get("schema_version") != 1 or library.get("session_id") != session:
            raise ValueError("폼 목록 파일의 버전과 세션을 확인하세요.")
        forms = library["forms"]
        if command == "list":
            return library
        form_id = payload["form_id"]
        version = payload["form_version"]
        if not isinstance(form_id, str) or not re.fullmatch("[a-f0-9]{32}", form_id) or type(version) is not int or version < 0:
            raise ValueError("폼 ID와 버전을 확인하세요.")
        history = forms.get(form_id, [])
        if command == "read":
            if not 1 <= version <= len(history):
                raise ValueError("이 세션에 해당 폼 버전이 없습니다.")
            entry = history[version - 1]
            digest = entry["sha256"]
            if not re.fullmatch("[a-f0-9]{64}", digest):
                raise ValueError("폼 해시가 잘못되었습니다.")
            data = (folder / (digest + ".json")).read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("저장된 폼 내용의 해시가 일치하지 않습니다.")
            return {"entry": entry, "definition_text": data.decode()}
        from workflow.common.management_gateway import parse_management_request_json
        definition = payload["definition_text"]
        if not isinstance(definition, str) or len(definition.encode()) > 500000:
            raise ValueError("폼 크기를 확인하세요.")
        parsed = parse_management_request_json(definition)
        if not isinstance(parsed, dict) or set(parsed) != {"steps"} or not isinstance(parsed["steps"], list):
            raise ValueError("폼의 steps 목록을 확인하세요.")
        name = payload["form_name"]
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise ValueError("폼 이름을 1~120자로 입력하세요.")
        data = json.dumps(parsed, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode()
        digest = hashlib.sha256(data).hexdigest()
        source = payload.get("copied_from")
        if source is not None:
            if (version != 0 or not isinstance(source, dict) or set(source) != {"form_id", "form_version"}
                    or not isinstance(source["form_id"], str) or type(source["form_version"]) is not int
                    or not 1 <= source["form_version"] <= len(forms.get(source["form_id"], []))):
                raise ValueError("복사할 원본 폼과 버전을 확인하세요.")
        entry = {"name": name.strip(), "version": version + 1, "sha256": digest, "copied_from": source}
        if len(history) == version + 1 and all(history[-1].get(k) == v for k, v in entry.items()):
            return {"form_id": form_id, "entry": history[-1]}
        if version != len(history):
            raise ValueError("다른 버전이 저장되었습니다. 최신 버전을 불러와 비교하세요.")
        entry["saved_at"] = datetime.now(timezone.utc).isoformat()
        blob = folder / (digest + ".json")
        if not blob.exists():
            replace_private_file(blob, data)
        elif blob.read_bytes() != data:
            raise ValueError("기존 폼 내용의 해시가 일치하지 않습니다.")
        forms.setdefault(form_id, []).append(entry)
        replace_private_file(index, json.dumps(library, ensure_ascii=False, indent=2).encode())
        return {"form_id": form_id, "entry": entry}
