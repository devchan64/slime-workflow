import React, {useEffect, useRef, useState} from "react";

export default function FormLibrary({session, call, addToMessage}) {
  const [forms, setForms] = useState({});
  const [selection, setSelection] = useState("");
  const [reference, setReference] = useState(null);
  const [name, setName] = useState("");
  const [definition, setDefinition] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState(null);
  function editDefinition(value) {
    setDefinition(value);
    setReview(null);
  }
  async function reviewWorkflow() {
    setReview(null);
    const checked = await call("workflow-review", {session_id: session, definition_text: definition});
    setReview(checked);
  }
  async function registerWorkflow() {
    const {session_id, run_id, steps} = review;
    await call("workflow-register", {session_id, run_id, steps});
    setNotice("대기열에 등록했습니다. 실행 ID " + run_id);
    setReview(null);
  }
  const pendingSave = useRef(null);
  const versions = Object.entries(forms).flatMap(([form_id, entries]) =>
    entries.slice().reverse().map(entry => ({
      key: form_id + "/" + entry.version,
      label: entry.name + " · v" + entry.version + " · " + form_id.slice(0, 8),
      form_id, form_version: entry.version
    }))
  );

  async function refresh() {
    const result = await call("form-list", {session_id: session});
    setForms(result.forms);
  }
  useEffect(() => { refresh().catch(error => setNotice(error.message)); }, [session]);

  async function run(operation) {
    setBusy(true);
    setNotice("");
    try { await operation(); }
    catch (error) { setNotice(error.message); }
    finally { setBusy(false); }
  }

  async function load() {
    const {form_id, form_version} = versions.find(version => version.key === selection);
    const result = await call("form-read", {session_id: session, form_id, form_version});
    editDefinition(result.definition_text);
    setName(result.entry.name);
    setReference({form_id, form_version});
    pendingSave.current = null;
    setNotice("선택한 버전을 불러왔습니다.");
  }

  async function save(copy) {
    const inputs = JSON.stringify([name, definition, reference, copy]);
    if (pendingSave.current?.inputs !== inputs) {
      const target = reference && !copy ? reference : {
        form_id: crypto.randomUUID().replaceAll("-", ""), form_version: 0
      };
      pendingSave.current = {inputs, payload: {
        ...target, session_id: session, form_name: name, definition_text: definition,
        ...(copy ? {copied_from: reference} : {})
      }};
    }
    const result = await call("form-save", pendingSave.current.payload);
    setReference({form_id: result.form_id, form_version: result.entry.version});
    setSelection(result.form_id + "/" + result.entry.version);
    pendingSave.current = null;
    setNotice(result.entry.name + " · v" + result.entry.version + " 저장됨");
    await refresh();
  }

  return <section className="panel" aria-label="세션 입력 폼">
    <fieldset disabled={busy}><legend>세션 입력 폼</legend>
      <label>저장된 버전 <select value={selection} onChange={event => setSelection(event.target.value)}>
        <option value="">버전 선택</option>
        {versions.map(version => <option key={version.key} value={version.key}>{version.label}</option>)}
      </select></label>
      <button onClick={() => run(refresh)}>목록 갱신</button>
      <button disabled={!selection} onClick={() => run(load)}>선택한 버전으로 초안 교체</button>
      <label>폼 이름 <input value={name} onChange={event => setName(event.target.value)}/></label>
      <label>워크플로우 정의 JSON <textarea value={definition} onChange={event => editDefinition(event.target.value)}/></label>
      <button disabled={!name.trim() || !definition.trim()} onClick={() => run(() => save(false))}>버전 저장</button>
      <button disabled={!reference || !name.trim() || !definition.trim()} onClick={() => run(() => save(true))}>별도 폼으로 복사</button>
      <button disabled={!definition.trim()} onClick={() => addToMessage(definition)}>대화 입력에 추가</button>
      <button disabled={!definition.trim()} onClick={() => run(reviewWorkflow)}>단계와 결과 연결 검토</button>
      {review && <section aria-label="워크플로우 등록 검토">
        <ol>{review.steps.map(step => <li key={step.id}>
          <strong>{step.id} · {step.generator}</strong>
          <pre>{JSON.stringify({inputs:step.inputs, bindings:step.bindings}, null, 2)}</pre>
        </li>)}</ol>
        <button onClick={() => run(registerWorkflow)}>검토한 단계 대기열 등록</button>
        <button onClick={() => setReview(null)}>등록 취소</button>
      </section>}
    </fieldset>
    <p role="status">{notice}</p>
  </section>;
}
