import ResultTable from "./ResultTable.jsx";
import StepBuilder from "./StepBuilder.jsx";
import React, {useEffect, useRef, useState} from "react";

export default function FormLibrary({session, proposalStep, messages, call, addToMessage, openRun}) {
  const [proposalId,setProposalId] = useState("");
  const proposals = messages.filter(message=>message.session_job_unique && message.job?.workflow_proposal);
  const selectedProposal = proposals.find(message=>message.job_id===proposalId);
  const [registeredRun,setRegisteredRun] = useState("");
  const [forms, setForms] = useState({});
  const [selection, setSelection] = useState("");
  const [reference, setReference] = useState(null);
  const [name, setName] = useState("");
  const [definition, setDefinition] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState(null);
  const [draftRevision,setDraftRevision] = useState(null);
  const edited = useRef(false);
  function editDefinition(value) {
    edited.current = true;
    setDefinition(value);
    setReview(null);
  }
  function restoreDraft(record) {
    if (record.session_id !== session || typeof record.definition_text !== "string" ||
        typeof record.revision !== "string") throw new Error("세션 초안 응답을 확인하세요.");
    setDefinition(record.definition_text);
    setDraftRevision(record.revision);
    setReview(null);
    setReference(null);
    setSelection("");
    setName("");
    edited.current = false;
  }
  useEffect(() => {
    let active = true;
    call("workflow-draft-read", {session_id:session}).then(record => {
      if (active && !edited.current) restoreDraft(record);
    }).catch(error => {if (active) setNotice(error.message);});
    return () => {active = false;};
  }, [session,call]);
  async function saveDraft() {
    const saved = await call("workflow-draft-save", {
      session_id:session, revision:draftRevision, definition_text:definition
    });
    if (saved.session_id !== session || typeof saved.revision !== "string")
      throw new Error("초안 저장 결과를 확인하세요.");
    setDraftRevision(saved.revision);
    setNotice("이 대화의 초안을 저장했습니다.");
  }
  async function reviewWorkflow() {
    setReview(null);
    const checked = await call("workflow-review", {session_id: session, definition_text: definition});
    setReview(checked);
  }
  async function registerWorkflow() {
    const {session_id, run_id, steps} = review;
    const result = await call("workflow-register", {session_id, run_id, steps});
    if (result.run_id !== run_id) throw new Error("등록 응답의 실행 ID를 확인하세요.");
    setRegisteredRun(run_id);
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
      {proposals.length>0 && <section>
        <label>대화에서 제안된 워크플로우 <select value={selectedProposal ? proposalId : ""} onChange={event=>setProposalId(event.target.value)}>
          <option value="">답변 선택</option>
          {proposals.map(message=><option key={message.job_id} value={message.job_id}>{message.text.slice(0,60)} · {message.job_id}</option>)}
        </select></label>
        <button disabled={!selectedProposal} onClick={()=>{
          editDefinition(selectedProposal.job.workflow_proposal);
          setReference(null);setSelection("");setName("");
          setNotice("선택한 답변의 제안으로 편집 초안을 교체했습니다.");
        }}>선택한 제안으로 초안 교체</button>
      </section>}
      <label>저장된 버전 <select value={selection} onChange={event => setSelection(event.target.value)}>
        <option value="">버전 선택</option>
        {versions.map(version => <option key={version.key} value={version.key}>{version.label}</option>)}
      </select></label>
      <button onClick={() => run(refresh)}>목록 갱신</button>
      <button disabled={!selection} onClick={() => run(load)}>선택한 버전으로 초안 교체</button>
      <label>폼 이름 <input value={name} onChange={event => setName(event.target.value)}/></label>
      <StepBuilder proposalStep={proposalStep} call={call} definition={definition} onChange={editDefinition}/>
      <label>워크플로우 정의 JSON <textarea value={definition} onChange={event => editDefinition(event.target.value)}/></label>
      <button disabled={draftRevision===null} onClick={()=>run(saveDraft)}>세션 초안 저장</button>
      <button onClick={()=>run(async()=>{
        restoreDraft(await call("workflow-draft-read",{session_id:session}));
        setNotice("서버에 저장된 초안을 불러왔습니다.");
      })}>서버 초안으로 편집 내용 교체</button>
      <button disabled={!name.trim() || !definition.trim()} onClick={() => run(() => save(false))}>버전 저장</button>
      <button disabled={!reference || !name.trim() || !definition.trim()} onClick={() => run(() => save(true))}>별도 폼으로 복사</button>
      <button disabled={!definition.trim()} onClick={() => addToMessage(definition)}>대화 입력에 추가</button>
      <button disabled={!definition.trim()} onClick={() => run(reviewWorkflow)}>단계와 결과 연결 검토</button>
      {review && <section aria-label="워크플로우 등록 검토">
        {review.steps.some(step=>Object.keys(step.bindings || {}).length>0) &&
          <ResultTable table={{
            title:"단계 간 결과 연결",
            summary:"선행 작업의 출력이 전달될 후속 작업과 입력 항목을 확인하세요.",
            columns:["선행 작업","출력 항목","후속 작업","입력 항목"],
            rows:review.steps.flatMap(step=>Object.entries(step.bindings || {}).map(([field,binding])=>
              [binding.from_step,binding.output,step.id,field]))
          }}/>}
        <ol>{review.steps.map(step => <li key={step.id}>
          <strong>{step.id} · {step.generator}</strong>
          <pre>{JSON.stringify({inputs:step.inputs, bindings:step.bindings}, null, 2)}</pre>
        </li>)}</ol>
        <button onClick={() => run(registerWorkflow)}>검토한 단계 대기열 등록</button>
        <button onClick={() => setReview(null)}>등록 취소</button>
      </section>}
    </fieldset>
    <p role="status">{notice}</p>
    {registeredRun && <button onClick={()=>openRun(registeredRun)}>마지막 등록 실행 보기</button>}
  </section>;
}
