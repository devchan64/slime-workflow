import KimodoMedia from "./KimodoMedia.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import TranslationResult from "./TranslationResult.jsx";
import {validWorkflowView} from "./workflowViewValidation.mjs";
import {sessionQueueStateLabel} from "./sessionQueueValidation.mjs";
import React, {useEffect, useId, useRef, useState} from "react";

const stepStates={ready:"접수 준비",waiting:"선행 단계 대기",awaiting_choice:"결과 선택 대기",submitting:"접수 중",queued:"대기 중",running:"실행 중",completed:"완료",failed:"실패",cancelled:"취소",blocked:"차단",unknown:"확인 중",paused:"일시 중지"};

async function workflowMutation(call,command,payload){
  const controller=new AbortController();let timedOut=false;
  const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
  try{return await untilAborted(call(command,payload,{signal:controller.signal}),controller.signal);}
  catch(problem){if(timedOut)throw new Error("요청 응답 시간이 초과됐습니다. 처리 여부를 확인하려면 결과를 갱신하세요.");throw problem;}
  finally{clearTimeout(timer);}
}

function MediaPreview({audio, result, session, run, call}) {
  const buttonRef=useRef(null),pending=useRef(null),mediaRef=useRef(null),retryRef=useRef(null),restoreMediaFocus=useRef(false);
  useEffect(()=>()=>{pending.current?.abort();pending.current=null;},[]);
  const [source,setSource] = useState("");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  useEffect(()=>{if(error && restoreMediaFocus.current){restoreMediaFocus.current=false;if(document.activeElement===document.body)retryRef.current?.focus();}},[error]);
  async function load() {
    if(pending.current)return;
    const controller=new AbortController();pending.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    const restoreFocus=document.activeElement===buttonRef.current || document.activeElement===retryRef.current;
    setBusy(true);
    setError("");
    try {
      const data = await untilAborted(call(audio ? "workflow-audio-preview" : "workflow-image-preview",
        {session_id:session, run_id:run, step_id:result.step_id},{signal:controller.signal}),controller.signal);
      if(pending.current!==controller || controller.signal.aborted)return;
      const encoded=audio ? data?.wav : data?.preview_png;
      if(typeof encoded!=="string" || !encoded || encoded.length%4!==0 || !/^[A-Za-z0-9+/]*={0,2}$/.test(encoded))throw new Error("미리보기 데이터 형식을 확인할 수 없습니다.");
      setSource((audio ? "data:audio/wav;base64," : "data:image/png;base64,")+encoded);
    } catch (problem) {if(pending.current===controller)setError(timedOut ? "미리보기 조회 시간이 초과됐습니다. 다시 시도해 주세요." : `미리보기를 불러오지 못했습니다. ${problem.message} 다시 시도해 주세요.`);}
    finally {clearTimeout(timer);if(pending.current===controller){pending.current=null;setBusy(false);if(restoreFocus)requestAnimationFrame(()=>{if(document.activeElement===document.body && buttonRef.current && !buttonRef.current.disabled)buttonRef.current.focus();});}}
  }
  return <><button ref={buttonRef} type="button" disabled={busy} aria-expanded={Boolean(source)} onClick={()=>source ? (setSource(""),setError("")) : load()}>{busy ? "불러오는 중" : source ? (audio ? "효과음 닫기" : "이미지 닫기") : (audio ? "효과음 듣기" : "이미지 보기")}</button>
    {source && !error && (audio ? <audio ref={mediaRef} controls src={source} aria-label={result.step_id+" 효과음 미리보기"} onError={event=>{if(event.currentTarget!==mediaRef.current)return;restoreMediaFocus.current=document.activeElement===mediaRef.current;setError("효과음 미리보기를 재생할 수 없습니다.");}}/> : <img ref={mediaRef} style={{maxWidth:"100%"}} src={source} alt={result.step_id + " 생성 결과"} onError={event=>{if(event.currentTarget!==mediaRef.current)return;restoreMediaFocus.current=document.activeElement===mediaRef.current;setError("이미지 미리보기를 표시할 수 없습니다.");}}/>)}
    {error && <><p role="alert">{error}</p>{source && <button ref={retryRef} type="button" disabled={busy} onClick={()=>{setSource("");load();}}>미리보기 다시 불러오기</button>}</>}</>;
}

function KimodoMotion({result}) {
  const buttonRef=useRef(null),pending=useRef(null);
  useEffect(()=>()=>{pending.current?.abort();pending.current=null;},[]);
  const [video,setVideo]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState("");
  async function load(){
    if(pending.current)return;
    const controller=new AbortController();pending.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    const restoreFocus=document.activeElement===buttonRef.current;
    setBusy(true);setError("");
    try{
      const job=await untilAborted(managementCommand("kimodo","status",{id:result.job_id},{signal:controller.signal}),controller.signal);
      if(pending.current!==controller || controller.signal.aborted)return;
      const directory="/kimodo/jobs/"+result.job_id+"/attempts/"+job.attempt+"/";
      if(job.status!=="completed" || !/^[a-f0-9]{32}$/.test(job.attempt) ||
         result.outputs.preview!==directory+"output-000.png" || job.video!==directory+"preview.mp4")
        throw new Error("보관한 프레임과 같은 실행 시도의 영상을 확인할 수 없습니다.");
      setVideo(job);
    }catch(problem){if(pending.current===controller)setError(timedOut ? "원본 모션 조회 시간이 초과됐습니다. 다시 시도해 주세요." : `원본 모션 영상을 불러오지 못했습니다. ${problem.message} 다시 시도해 주세요.`);}
    finally{clearTimeout(timer);if(pending.current===controller){pending.current=null;setBusy(false);if(restoreFocus)requestAnimationFrame(()=>{if(document.activeElement===document.body && buttonRef.current && !buttonRef.current.disabled)buttonRef.current.focus();});}}
  }
  return <section aria-label="Kimodo 모션 결과">
    <button ref={buttonRef} type="button" disabled={busy} aria-expanded={Boolean(video)} onClick={()=>video ? setVideo("") : load()}>{busy ? "불러오는 중" : video ? "원본 모션 영상 닫기" : "원본 모션 영상 보기"}</button>
    {video && <KimodoMedia id={result.job_id} job={video}/>}
    {error && <p role="alert">{error}</p>}
  </section>;
}

export default function WorkflowResults(props) {
  return <WorkflowResultsForRun key={JSON.stringify([props.session,props.run])} {...props}/>;
}

function WorkflowResultsForRun({session, run, call, close, openRun, editNextStep}) {
  const staleHelpId=useId();
  const refreshRef=useRef(null),restoreRefreshFocus=useRef(false);
  const cancelReviewRef=useRef(null),cancelTriggerRef=useRef(null),restoreCancelFocus=useRef(false),cancelSubmittedFocus=useRef(false);
  const mutationPending=useRef(false),viewPending=useRef(true),requiresRefresh=useRef(true);
  const [catalog,setCatalog] = useState({});
  const [catalogError,setCatalogError]=useState(""),[catalogRevision,retryCatalog]=useState(0),[catalogLoading,setCatalogLoading]=useState(true),[catalogReady,setCatalogReady]=useState(false);
  const catalogRetryRef=useRef(null),catalogStatusRef=useRef(null),restoreCatalogFocus=useRef(false);
  useEffect(()=>{if(!catalogLoading && restoreCatalogFocus.current){restoreCatalogFocus.current=false;if(document.activeElement===document.body)(catalogError ? catalogRetryRef : catalogStatusRef).current?.focus();}},[catalogLoading,catalogError]);
  useEffect(()=>{
    let active=true,timedOut=false;const controller=new AbortController();
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setCatalogError("");setCatalogLoading(true);
    untilAborted(call("workflow-catalog",{},{signal:controller.signal}),controller.signal).then(data=>{
      if(!data?.generators || typeof data.generators!=="object" || Array.isArray(data.generators) || Object.values(data.generators).some(spec=>!spec || typeof spec!=="object" || typeof spec.label!=="string" || !spec.inputs || typeof spec.inputs!=="object" || Array.isArray(spec.inputs) || Object.values(spec.inputs).some(input=>!input || typeof input!=="object" || Array.isArray(input) || typeof input.type!=="string" || (input.label!=null && typeof input.label!=="string"))))throw new Error("생성기 목록 형식을 확인할 수 없습니다.");
      if(active){setCatalog(data.generators);setCatalogReady(true);}
    }).catch(problem=>{if(active)setCatalogError(timedOut ? "생성기 목록 조회 시간이 초과됐습니다." : problem.message || "생성기 목록을 불러오지 못했습니다.");}).finally(()=>{clearTimeout(timer);if(active)setCatalogLoading(false);});
    return ()=>{active=false;clearTimeout(timer);controller.abort();};
  },[call,catalogRevision]);
  const [view,setView] = useState(null);
  const [observation,setObservation] = useState(null);
  const [error,setError] = useState("");
  const [busy,setBusy] = useState(false);
  const [confirmCancel,setConfirmCancel] = useState(false);
  useEffect(()=>{if(confirmCancel)cancelReviewRef.current?.focus();else if(restoreCancelFocus.current){restoreCancelFocus.current=false;if(document.activeElement===document.body)cancelTriggerRef.current?.focus();}},[confirmCancel]);
  useEffect(()=>{if(!busy && cancelSubmittedFocus.current){cancelSubmittedFocus.current=false;if(document.activeElement===document.body)refreshRef.current?.focus();}},[busy]);
  const [revision,setRevision] = useState(0);
  useEffect(() => {
    let active = true,timedOut=false;
    const controller=new AbortController();
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    viewPending.current=true;
    setBusy(true); setError("");
    untilAborted(call("workflow-view", {session_id:session,run_id:run},{signal:controller.signal}),controller.signal)
      .then(value => {
        if(!active)return;
        if(!validWorkflowView(value,run))throw new Error("실행 결과 형식을 확인할 수 없습니다. 결과를 다시 갱신하세요.");
        requiresRefresh.current=false;
        setView(value);setObservation({run,time:new Date()});
      })
      .catch(problem => { if (active) {requiresRefresh.current=true;setError(timedOut ? "결과 조회 시간이 초과됐습니다. 다시 갱신해 주세요." : problem.message);} })
      .finally(() => { if (active) {
        clearTimeout(timer);
        viewPending.current=false;setBusy(false);
        if(restoreRefreshFocus.current){restoreRefreshFocus.current=false;requestAnimationFrame(()=>{if(document.activeElement===document.body && refreshRef.current && !refreshRef.current.disabled)refreshRef.current.focus();});}
      } });
    return () => {active=false;clearTimeout(timer);controller.abort();};
  }, [session,run,call,revision]);
  useEffect(() => {
    if (busy || error || confirmCancel || !view?.steps.some(step =>
      ["ready","waiting","submitting"].includes(step.state))) return;
    const timer = setTimeout(() => {if(!mutationPending.current && !viewPending.current){viewPending.current=true;setBusy(true);setRevision(value => value+1);}}, 3000);
    return () => clearTimeout(timer);
  }, [view,busy,error,confirmCancel]);
  const [connectionNotice,setConnectionNotice]=useState("");
  async function select(choice) {
    if(mutationPending.current || viewPending.current || requiresRefresh.current)return;
    mutationPending.current=true;
    setBusy(true); setError("");
    try {
      const {step_id,input_field,source_request,digest} = choice;
      const updated = await workflowMutation(call,"workflow-select",{session_id:session,run_id:run,step_id,input_field,source_request,digest});
      if(!validWorkflowView(updated,run) || !updated.choices.some(item=>item.selected && item.step_id===step_id &&
          item.input_field===input_field && item.source_request===source_request && item.digest===digest))
        throw new Error("결과 연결을 확인할 수 없습니다. 결과를 갱신하세요.");
      setView(updated);
      setConnectionNotice(step_id+" 단계의 "+input_field+" 입력에 결과를 연결했습니다.");
    } catch (problem) {requiresRefresh.current=true;setError((problem.message || "결과 연결을 확인할 수 없습니다.")+" 결과를 갱신해 처리 여부를 확인하세요.");}
    finally {mutationPending.current=false;setBusy(false);}
  }
  async function retry(step) {
    if(mutationPending.current || viewPending.current || requiresRefresh.current)return;
    mutationPending.current=true;
    setBusy(true); setError("");
    try {
      const result = await workflowMutation(call,"workflow-retry", {
        session_id:session, run_id:run, step_id:step.step_id, source_request:step.request_id
      });
      const link = result.retries?.find(item => item.source_request===step.request_id &&
        item.source_run===run && item.retry_run===result.run_id);
      if (!link) throw new Error("재시도 연결을 확인할 수 없습니다. 실행 결과를 갱신하세요.");
      setView(current => ({...current, retries:[...(current.retries || []).filter(item =>
        item.source_request!==step.request_id),link]}));
    } catch (problem) {requiresRefresh.current=true;setError((problem.message || "재시도 접수를 확인할 수 없습니다.")+" 결과를 갱신해 처리 여부를 확인하세요.");}
    finally {mutationPending.current=false;setBusy(false);}
  }
  const activeSteps = view?.steps.filter(step =>
    ["ready","waiting","awaiting_choice","submitting"].includes(step.state) && !step.cancel_delivery) || [];
  async function cancelRun() {
    if(mutationPending.current || viewPending.current || requiresRefresh.current)return;
    mutationPending.current=true;
    cancelSubmittedFocus.current=Boolean(cancelReviewRef.current?.contains(document.activeElement));
    setConfirmCancel(false);
    setBusy(true);
    setError("");
    try {
      const updated = await workflowMutation(call,"workflow-cancel",{session_id:session,run_id:run});
      if (!validWorkflowView(updated,run)) throw new Error("취소 후 실행 상태를 확인할 수 없습니다. 결과를 갱신하세요.");
      setView(updated);
    } catch (problem) {requiresRefresh.current=true;setError((problem.message || "취소 결과를 확인할 수 없습니다.")+" 결과를 갱신해 처리 여부를 확인하세요.");}
    finally {mutationPending.current=false;setBusy(false);}
  }
  return <section className="workflow-result" aria-label="워크플로우 결과">
    <header className="workflow-result-header"><div><h3 tabIndex={-1}>워크플로우 결과</h3><span>실행 ID</span><JobIdentifier id={run} label="실행 ID" compact/></div>
      <div className="workflow-result-actions"><button ref={refreshRef} disabled={busy} onClick={()=>{if(mutationPending.current || viewPending.current)return;viewPending.current=true;setBusy(true);restoreRefreshFocus.current=document.activeElement===refreshRef.current;setConfirmCancel(false);setRevision(value=>value+1);}}>결과 갱신</button>
      <button onClick={close}>결과 닫기</button></div></header>
    <p role="status">{connectionNotice}</p>
    <p role="status">{busy && "처리 중 · "}{observation?.run===run ? `마지막 조회 성공 · ${observation.time.toLocaleString("ko-KR")}` : busy ? "결과 정보를 확인하고 있습니다." : "조회 시각을 확인할 수 없습니다."}</p>
    {error && <p role="alert">{error}</p>}
    {editNextStep && (catalogError ? <div><p role="alert">{catalogError}{catalogReady && " 이전 목록이 표시됩니다."}</p><button ref={catalogRetryRef} type="button" onClick={()=>{restoreCatalogFocus.current=document.activeElement===catalogRetryRef.current;retryCatalog(value=>value+1);}}>생성기 목록 다시 조회</button></div> : <p ref={catalogStatusRef} tabIndex={-1} role="status">{catalogLoading ? "생성기 목록 조회 중…" : catalogReady ? "생성기 목록을 확인했습니다." : "생성기 목록을 확인하지 못했습니다."}</p>)}
    {error && view && <p id={staleHelpId} role="status">아래 내용은 마지막으로 조회한 결과입니다. 결과를 갱신할 때까지 실행 취소·재시도·결과 연결을 사용할 수 없습니다.</p>}
    {view && <>
      {activeSteps.length>0 && (confirmCancel ?
        <section ref={cancelReviewRef} tabIndex={-1} aria-label="실행 취소 확인">
          <p>실행 {run}의 대기 단계를 취소하고 접수 중인 단계에 중지를 요청합니다.</p>
          <p>{activeSteps.map(step=>step.step_id).join(", ")}</p>
          <button disabled={busy || Boolean(error)} aria-describedby={error ? staleHelpId : undefined} onClick={cancelRun}>이 실행 취소 확정</button>
          <button type="button" onClick={()=>{restoreCancelFocus.current=Boolean(cancelReviewRef.current?.contains(document.activeElement));setConfirmCancel(false);}}>실행 유지</button>
        </section> :
        <button ref={cancelTriggerRef} type="button" disabled={busy || Boolean(error)} aria-describedby={error ? staleHelpId : undefined} onClick={()=>setConfirmCancel(true)}>워크플로우 취소 검토</button>)}
      {view.steps.map(step => <div className="workflow-step" key={step.step_id}>
        <p><strong>{step.step_id}</strong> <span className="workflow-step-status">{sessionQueueStateLabel(stepStates,step.state)}</span>{step.cancel_delivery && " · 중지 요청 " +
          sessionQueueStateLabel({pending:"전달 대기",unconfirmed:"전달 확인 중",acknowledged:"전달됨"},step.cancel_delivery)}</p>
        {Object.entries(step.bindings || {}).map(([input,source])=><p key={input}>
          {source.from_step}.{source.output} → {step.step_id}.{input}</p>)}
        {["failed","cancelled"].includes(step.state) &&
          !view.retries?.some(item=>item.source_request===step.request_id) &&
          <button disabled={busy || Boolean(error)} aria-describedby={error ? staleHelpId : undefined} onClick={()=>retry(step)}>{step.step_id} 단계의 저장된 입력으로 재시도</button>}
        {step.state==="blocked" && <p>{step.step_id} · {step.block_reason}</p>}
      </div>)}
      {view.retries?.map(link=><p key={link.source_request}>{link.step_id} ·
        {link.retry_run===run ?
          <button onClick={()=>openRun(link.source_run)}>원래 실행 보기</button> :
          <button onClick={()=>openRun(link.retry_run)}>재시도 실행 보기</button>}
      </p>)}
      {view.results.length===0 && <p>아직 기록된 결과가 없습니다.</p>}
      {view.results.map(result => <section className="workflow-output" key={result.attempt_id}><h4>{result.step_id}</h4><JobIdentifier id={result.job_id} compact/>
        {typeof result.outputs.text === "string" && (view.steps.some(step=>step.step_id===result.step_id && step.generator==="prompt-translation")
          ? <TranslationResult job={result.job_id} text={result.outputs.text}/> : <pre>{result.outputs.text}</pre>)}
        {view.steps.some(step=>step.step_id===result.step_id && step.generator==="kimodo") &&
          <KimodoMotion key={JSON.stringify([result.job_id,result.outputs.preview])} result={result}/>}
        {(result.outputs.audio || result.outputs.preview) &&
          <MediaPreview key={JSON.stringify([result.job_id,result.output_metadata?.sha256,result.outputs.preview,result.outputs.audio?.sha256,Boolean(result.outputs.audio)])} audio={Boolean(result.outputs.audio)} {...{result,session,run,call}}/>}
        {view.choices.filter(choice=>choice.source_request===result.attempt_id && choice.digest===result.output_metadata?.sha256).map(choice=>{
          const binding=view.steps.find(step=>step.step_id===choice.step_id)?.bindings?.[choice.input_field];
          return <p key={choice.step_id+"/"+choice.input_field}>
            {result.step_id}.{binding?.output} → {choice.step_id}.{choice.input_field}{" "}
            {choice.selected ? "연결됨" : <button disabled={busy || Boolean(error)} aria-describedby={error ? staleHelpId : undefined} onClick={()=>select(choice)}>이 결과를 다음 입력에 연결</button>}
          </p>;
        })}
        {editNextStep && typeof result.outputs.text==="string" && <label>새 작업의 입력으로 사용
          <select value="" onChange={event=>{
            const [generator,field]=JSON.parse(event.target.value);
            editNextStep({generator,inputs:{[field]:result.outputs.text},source:result.job_id});
          }}>
            <option value="">생성기와 입력 선택</option>
            {Object.entries(catalog).flatMap(([generator,spec])=>Object.entries(spec.inputs)
              .filter(([,input])=>input.type==="text" && !input.choices && (!input.max_length || Array.from(result.outputs.text).length<=input.max_length))
              .map(([field,input])=><option key={generator+"/"+field} value={JSON.stringify([generator,field])}>{spec.label} · {input.label || field}</option>))}
          </select></label>}
      </section>)}
    </>}
  </section>;
}
