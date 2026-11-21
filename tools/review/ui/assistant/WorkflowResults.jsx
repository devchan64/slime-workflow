import React, {useEffect, useState} from "react";

function MediaPreview({audio, result, session, run, call}) {
  const [source,setSource] = useState("");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  async function load() {
    setBusy(true);
    setError("");
    try {
      const data = await call(audio ? "workflow-audio-preview" : "workflow-image-preview",
        {session_id:session, run_id:run, step_id:result.step_id});
      setSource(audio ? "data:audio/wav;base64," + data.wav : "data:image/png;base64," + data.preview_png);
    } catch (problem) {setError(problem.message);}
    finally {setBusy(false);}
  }
  if (source) return audio ? <audio controls src={source}/> :
    <img style={{maxWidth:"100%"}} src={source} alt={result.step_id + " 생성 결과"}/>;
  return <><button disabled={busy} onClick={load}>{audio ? "효과음 듣기" : "이미지 보기"}</button>
    {error && <p role="alert">{error}</p>}</>;
}

export default function WorkflowResults({session, run, call, close, openRun}) {
  const [view,setView] = useState(null);
  const [error,setError] = useState("");
  const [busy,setBusy] = useState(false);
  const [confirmCancel,setConfirmCancel] = useState(false);
  const [revision,setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setBusy(true); setError("");
    call("workflow-view", {session_id:session,run_id:run})
      .then(value => { if (active && value.run_id===run) setView(value); })
      .catch(problem => { if (active) setError(problem.message); })
      .finally(() => { if (active) setBusy(false); });
    return () => {active=false;};
  }, [session,run,call,revision]);
  async function select(choice) {
    setBusy(true); setError("");
    try {
      const {step_id,input_field,source_request,digest} = choice;
      const updated = await call("workflow-select",{session_id:session,run_id:run,step_id,input_field,source_request,digest});
      if (updated.run_id===run) setView(updated);
    } catch (problem) {setError(problem.message);}
    finally {setBusy(false);}
  }
  async function retry(step) {
    setBusy(true); setError("");
    try {
      const result = await call("workflow-retry", {
        session_id:session, run_id:run, step_id:step.step_id, source_request:step.request_id
      });
      const link = result.retries?.find(item => item.source_request===step.request_id &&
        item.source_run===run && item.retry_run===result.run_id);
      if (!link) throw new Error("재시도 연결을 확인할 수 없습니다. 실행 결과를 갱신하세요.");
      setView(current => ({...current, retries:[...(current.retries || []).filter(item =>
        item.source_request!==step.request_id),link]}));
    } catch (problem) {setError(problem.message);}
    finally {setBusy(false);}
  }
  const activeSteps = view?.steps.filter(step =>
    ["ready","waiting","awaiting_choice","submitting"].includes(step.state) && !step.cancel_delivery) || [];
  async function cancelRun() {
    setConfirmCancel(false);
    setBusy(true);
    setError("");
    try {
      const updated = await call("workflow-cancel",{session_id:session,run_id:run});
      if (updated.run_id !== run) throw new Error("실행 ID가 일치하지 않습니다.");
      setView(updated);
    } catch (problem) {setError(problem.message);}
    finally {setBusy(false);}
  }
  return <section aria-label="워크플로우 결과">
    <h3>워크플로우 결과</h3><code>{run}</code>
    <button disabled={busy} onClick={()=>{setConfirmCancel(false);setRevision(value=>value+1);}}>결과 갱신</button>
    <button onClick={close}>결과 닫기</button>
    {error && <p role="alert">{error}</p>}
    {view && <>
      {activeSteps.length>0 && (confirmCancel ?
        <section aria-label="실행 취소 확인">
          <p>실행 {run}의 대기 단계를 취소하고 접수 중인 단계에 중지를 요청합니다.</p>
          <p>{activeSteps.map(step=>step.step_id).join(", ")}</p>
          <button disabled={busy} onClick={cancelRun}>이 실행 취소 확정</button>
          <button onClick={()=>setConfirmCancel(false)}>실행 유지</button>
        </section> :
        <button disabled={busy} onClick={()=>setConfirmCancel(true)}>워크플로우 취소 검토</button>)}
      {view.steps.map(step => <div key={step.step_id}>
        <p>{step.step_id} · {step.state}{step.cancel_delivery && " · 중지 요청 " +
          ({pending:"전달 대기",unconfirmed:"전달 확인 중",acknowledged:"전달됨"}[step.cancel_delivery] || step.cancel_delivery)}</p>
        {Object.entries(step.bindings || {}).map(([input,source])=><p key={input}>
          {source.from_step}.{source.output} → {step.step_id}.{input}</p>)}
        {["failed","cancelled"].includes(step.state) &&
          !view.retries?.some(item=>item.source_request===step.request_id) &&
          <button disabled={busy} onClick={()=>retry(step)}>{step.step_id} 단계의 저장된 입력으로 재시도</button>}
        {step.state==="blocked" && <p>{step.step_id} · {step.block_reason}</p>}
      </div>)}
      {view.retries?.map(link=><p key={link.source_request}>{link.step_id} ·
        {link.retry_run===run ?
          <button onClick={()=>openRun(link.source_run)}>원래 실행 보기</button> :
          <button onClick={()=>openRun(link.retry_run)}>재시도 실행 보기</button>}
      </p>)}
      {view.results.length===0 && <p>아직 기록된 결과가 없습니다.</p>}
      {view.results.map(result => <section key={result.attempt_id}><h4>{result.step_id} · {result.job_id}</h4>
        {typeof result.outputs.text === "string" && <pre>{result.outputs.text}</pre>}
        {(result.outputs.audio || result.outputs.preview) &&
          <MediaPreview audio={Boolean(result.outputs.audio)} {...{result,session,run,call}}/>}
      </section>)}
      {view.choices.filter(choice=>!choice.selected).map(choice=>
        <button key={choice.step_id+"/"+choice.input_field} disabled={busy} onClick={()=>select(choice)}>
          {choice.step_id}.{choice.input_field}에 검토한 결과 전달
        </button>)}
    </>}
  </section>;
}
