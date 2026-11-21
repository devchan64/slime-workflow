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

export default function WorkflowResults({session, run, call, close}) {
  const [view,setView] = useState(null);
  const [error,setError] = useState("");
  const [busy,setBusy] = useState(false);
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
  return <section aria-label="워크플로우 결과">
    <h3>워크플로우 결과</h3><code>{run}</code>
    <button disabled={busy} onClick={()=>setRevision(value=>value+1)}>결과 갱신</button>
    <button onClick={close}>결과 닫기</button>
    {error && <p role="alert">{error}</p>}
    {view && <>
      {view.steps.map(step => <div key={step.step_id}>
        {Object.entries(step.bindings || {}).map(([input,source])=><p key={input}>
          {source.from_step}.{source.output} → {step.step_id}.{input}</p>)}
        {step.state==="blocked" && <p>{step.step_id} · {step.block_reason}</p>}
      </div>)}
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
