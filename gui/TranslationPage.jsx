import JobStatus from "./JobStatus.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import JobIdentifier from "./JobIdentifier.jsx";
import RecordFolder from "./RecordFolder.jsx";
import GenerationProgress from "./GenerationProgress.jsx";
import {useLiveRefresh} from "./LiveRefresh.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import ActionButton from "./ActionButton.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import React, {useEffect,useId,useRef,useState} from "react";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import TranslationEvidence from "./TranslationEvidence.jsx";
import TranslationResult from "./TranslationResult.jsx";
import SavedGeneratorInputs from "./SavedGeneratorInputs.jsx";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import GeneratorSectionNavigation,{openGeneratorHistory} from "./GeneratorSectionNavigation.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import {parseTranslationGlossary} from "./translationGlossary.mjs";
import {generationReady} from "./generationReady.mjs";

const service="prompt-translation";
const callHermes=(command,payload,options)=>managementCommand("hermes-agent","hermes-"+command,payload,options);

export function TranslationNotice({message,error=false}) {
  return <p role={error ? "alert" : "status"}>{message}</p>;
}

export default function TranslationPage({embedded=false,session:embeddedSession=""}={}) {
  const query=new URLSearchParams(location.search);
  const [text,setText]=useState(""),[language,setLanguage]=useState("en"),[terms,setTerms]=useState("");
  const inputRef=useRef({text,language,terms});
  inputRef.current={text,language,terms};
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[notice,setNoticeState]=useState(""),[noticeError,setNoticeError]=useState(false),[model,setModel]=useState(null);
  function setNotice(message,{error=false}={}){setNoticeState(message);setNoticeError(error);}
  const reviewEpoch=useRef(0),reviewRefState=useRef(pending);
  reviewRefState.current=pending;
  const [modelError,setModelError]=useState("");
  const [termsError,setTermsError]=useState("");
  const termsHelp=useId(),termsErrorId=useId(),lockedId=useId(),termsRef=useRef(null),textRef=useRef(null),reviewRef=useRef(null),reviewOrigin=useRef(null);
  const resultRef=useRef(null),focusResult=useRef(false),inputRegion=useRef(null),inputCard=useRef(null),historyRegion=useRef(null),restoreFrame=useRef(null);
  const [job,setJob]=useState(embedded ? "" : query.get("job") || ""),[record,setRecord]=useState(null);
  const [statusError,setStatusError]=useState("");
  const [statusCheckedAt,setStatusCheckedAt]=useState(null),[statusFailedAt,setStatusFailedAt]=useState(null);
  const [revision,setRevision]=useState(0);
  const [historyRevision,setHistoryRevision]=useState(0);
  const sending=useRef(false),submitRequest=useRef(null);
  const live=useLiveRefresh(()=>setRevision(value=>value+1),Boolean(job) && (!record || ["queued","running"].includes(record.status?.status)));
  useEffect(()=>{if(!embedded)document.title="프롬프트 번역";},[embedded]);
  useEffect(()=>()=>{if(restoreFrame.current!==null)cancelAnimationFrame(restoreFrame.current);const current=submitRequest.current;submitRequest.current=null;current?.controller.abort();},[]);
  useEffect(()=>{setStatusError("");setStatusCheckedAt(null);setStatusFailedAt(null);},[job]);
  useEffect(()=>{if(!pending)return;const origin=reviewOrigin.current;reviewOrigin.current=null;const frame=requestAnimationFrame(()=>{if((document.activeElement===document.body || document.activeElement===origin) && reviewRef.current?.isConnected)reviewRef.current.focus();});return ()=>cancelAnimationFrame(frame);},[pending]);
  useEffect(()=>{if(focusResult.current && job && record?.id===job && resultRef.current){focusResult.current=false;if(document.activeElement===document.body){resultRef.current.focus({preventScroll:true});resultRef.current.scrollIntoView({block:"start",inline:"nearest"});}}},[job,record]);
  useEffect(()=>{
    if(!job)return;
    let active=true,timedOut=false;
    const controller=new AbortController();
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    async function read(){
      try{
        const next=await untilAborted(managementCommand(service,"translation-status",{id:job},{signal:controller.signal}),controller.signal);
        if(!active)return;
        if(next?.id!==job)throw new Error("작업 ID가 일치하지 않습니다.");
        if(!next.status || typeof next.status!=="object" || typeof next.status.status!=="string")throw new Error("작업 상태 응답을 확인할 수 없습니다.");
        setRecord(next);setStatusCheckedAt(new Date());setStatusError("");

      }catch(error){if(active){setStatusFailedAt(new Date());setStatusError(timedOut ? "상태 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(error));}}
      finally{clearTimeout(timeout);}
    }
    read();return()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[job,revision]);
  function review(){
    reviewEpoch.current++;
    const current=inputRef.current;
    if(!current.text.trim()){setNotice("번역할 한국어 원문을 입력하세요.",{error:true});textRef.current?.focus();return;}
    try{
      const glossary=parseTranslationGlossary(current.terms);
      reviewOrigin.current=document.activeElement;
      setPending({text:current.text,target_language:current.language,glossary});setTermsError("");setNotice("");
    }catch(error){setTermsError(error.message);termsRef.current?.focus();}
  }
  function cancelReview(){
    const restore=reviewRef.current?.contains(document.activeElement),epoch=reviewEpoch.current;
    setPending(null);
    if(restoreFrame.current!==null)cancelAnimationFrame(restoreFrame.current);
    if(restore)restoreFrame.current=requestAnimationFrame(()=>{restoreFrame.current=null;if(epoch===reviewEpoch.current)restoreLostFocus(document,textRef.current);});
  }
  async function submit(){
    if(!pending || sending.current || !generationReady(model))return;
    const request={controller:new AbortController(),timedOut:false};submitRequest.current=request;
    sending.current=true;setBusy(true);
    const timeout=setTimeout(()=>{request.timedOut=true;request.controller.abort();},30000);
    try{
      const result=await untilAborted(managementCommand(service,"translation-submit",pending,{signal:request.controller.signal}),request.controller.signal);
      if(submitRequest.current!==request)return;
      if(typeof result?.id!=="string" || !result.id.trim())throw new Error("접수 ID를 확인할 수 없습니다.");
      setRecord(null);setJob(result.id);setNotice("번역 대기열에 등록했습니다.");
    }catch(error){if(submitRequest.current===request)setNotice((request.timedOut ? "접수 응답 시간이 초과됐습니다." : requestErrorMessage(error))+" · 다시 요청하기 전에 이력을 조회해 접수 여부를 확인하세요."+(job ? " 아래 작업은 이전에 선택한 작업입니다." : ""),{error:true});}
    finally{clearTimeout(timeout);if(submitRequest.current===request){submitRequest.current=null;setPending(null);sending.current=false;setBusy(false);}}
  }
  async function readJob(id,{signal}={}){
    const inputAtStart=inputRef.current,reviewAtStart=reviewEpoch.current,focusAtStart=document.activeElement;
    const controller=new AbortController();let timedOut=false;
    const abort=()=>controller.abort();if(signal?.aborted)controller.abort();else signal?.addEventListener("abort",abort,{once:true});
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      const record=await untilAborted(managementCommand(service,"translation-status",{id},{signal:controller.signal}),controller.signal);
      const input=record?.request;
      if(record?.id!==id || !input || typeof input.text!=="string" || !["en","zh-CN"].includes(input.target_language) ||
        (input.glossary!=null && (!Array.isArray(input.glossary) || input.glossary.some(term=>!term || typeof term.source!=="string" || typeof term.target!=="string"))))
        throw new Error("저장된 번역 입력 형식을 확인할 수 없습니다.");
      return {...record,inputAtStart,reviewAtStart,focusAtStart};
    }catch(error){if(timedOut)throw new Error("저장 입력 조회 시간이 초과됐습니다. 다시 조회하세요.");throw error;}
    finally{clearTimeout(timeout);signal?.removeEventListener("abort",abort);}
  }
  function restore(input,record){
    const before=record.inputAtStart,current=inputRef.current;
    if(record.reviewAtStart!==reviewEpoch.current || reviewRefState.current)throw new Error("조회 중 번역 요청을 검토해 이력 입력을 적용하지 않았습니다.");
    if(before.text!==current.text || before.language!==current.language || before.terms!==current.terms)throw new Error("입력 조회 중 작성 내용이 변경되어 적용하지 않았습니다.");
    const restoredTerms=(input.glossary||[]).map(term=>term.source+" => "+term.target).join("\n");
    inputRef.current={text:input.text,language:input.target_language,terms:restoredTerms};
    setText(input.text);setLanguage(input.target_language);
    setTerms(restoredTerms);setTermsError("");
    if(inputCard.current)inputCard.current.open=true;
    setNotice((record.id ? record.id+"의 번역 입력을 불러왔습니다. " : "이력의 번역 입력을 불러왔습니다. ")+"내용을 확인하거나 수정하세요.");
    if(restoreFrame.current!==null)cancelAnimationFrame(restoreFrame.current);
    restoreFrame.current=requestAnimationFrame(()=>{restoreFrame.current=null;if(record.reviewAtStart===reviewEpoch.current && !reviewRefState.current && (document.activeElement===record.focusAtStart || document.activeElement===document.body) && textRef.current?.isConnected && !textRef.current.disabled)textRef.current.focus();});
  }
  return <section className={embedded ? "translation-page generator-page-common" : "translation-page translation-standalone generator-page-common"} style={embedded ? {minWidth:0} : undefined}>
    {!embedded && <a href={"/management/assistant/"+(query.has("session")?"?"+new URLSearchParams({session:query.get("session")}):"")}>헤르메스 대화</a>}
    <h1 className={embedded ? "embedded-page-title" : undefined}>프롬프트 번역</h1>
    <p>TranslateGemma 4B · ROCm BF16 · <a href="https://ai.google.dev/gemma/terms">Gemma 이용약관</a></p>
    <GeneratorChangelog generator={service} card/>
    <GeneratorSectionCard title="사용설명" summary="사용 방법과 제한 사항" className="vace-usage-card">
      <p>한국어 프롬프트를 영어 또는 중국어 간체로 번역합니다.</p>
      <ol><li>한국어 원문과 목표 언어를 입력합니다.</li><li>필요하면 확인할 용어를 한 줄에 하나씩 <code>원문 =&gt; 번역어</code> 형식으로 입력합니다.</li><li>번역 요청을 검토하고 확인한 뒤 대기열에 추가합니다. 결과는 생성 이력에서 확인합니다.</li></ol>
      <p>번역 결과와 지정한 용어가 의도에 맞는지 확인한 뒤 사용하세요. 모델이 준비되지 않으면 모델 준비 상태에서 필요한 조치를 확인하세요.</p>
    </GeneratorSectionCard>
    <GeneratorSectionNavigation inputRef={inputRegion} historyRef={historyRegion} resultRef={resultRef} resultReady={Boolean(job)} openOnNavigate/>
    <GeneratorSectionCard title="모델 준비 상태" summary={modelError ? "조회 실패" : !model ? "확인 중" : generationReady(model) ? "준비됨" : "준비 필요"}><ModelReadiness session={embeddedSession || query.get("session") || ""} service={service} onStatus={setModel} onError={setModelError}/></GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={historyRevision} onOpenResult={id=>openGeneratorHistory(historyRegion,id,()=>{focusResult.current=true;setRecord(null);setJob(id);})}/>
    {pending && <p id={lockedId}>아래 번역 요청을 확인하거나 입력 수정을 선택하세요.</p>}
    <fieldset className="translation-workflow" disabled={Boolean(pending)} aria-describedby={pending ? lockedId : undefined}><legend className="generator-visually-hidden">번역 입력과 이력</legend><GeneratorSectionCard title="번역 입력" summary="원문과 용어" defaultOpen cardRef={inputCard}><div ref={inputRegion} className="translation-input" tabIndex={-1} aria-label="번역 입력"><label>한국어 원문 <textarea ref={textRef} value={text} onChange={e=>{const value=e.target.value;inputRef.current={...inputRef.current,text:value};setText(value);}}/></label>
      <label>목표 언어 <select value={language} onChange={e=>{const value=e.target.value;inputRef.current={...inputRef.current,language:value};setLanguage(value);}}><option value="en">영어</option><option value="zh-CN">중국어 간체</option></select></label>
      <label>확인할 용어 <textarea ref={termsRef} placeholder="원문 => 번역어" aria-describedby={termsError?`${termsHelp} ${termsErrorId}`:termsHelp} aria-invalid={Boolean(termsError)} value={terms} onChange={e=>{const value=e.target.value;inputRef.current={...inputRef.current,terms:value};setTerms(value);setTermsError("");}}/></label>
      <small id={termsHelp}>선택 사항 · 한 줄에 하나씩 입력하세요. 예: 로봇 =&gt; robot</small>
      {termsError && <p id={termsErrorId} role="alert">{termsError}</p>}
      <p><PromptWordCount text={text} final/></p>
      <TranslationEvidence source={text} call={callHermes}/>
      <ActionButton reasons={[!text.trim() && "번역할 한국어 원문을 입력하세요."]} onClick={review}>번역 요청 검토</ActionButton></div></GeneratorSectionCard>
      <div ref={historyRegion} aria-label="번역 이력"><GeneratorHistory card allowPriority onSelectedDeleted={(id,message)=>{if(job===id){setJob("");setRecord(null);}setNotice(message);setHistoryRevision(v=>v+1);}} key={historyRevision} service={service} statusCommand="translation-status" readJobWithSignal={readJob} resultId={job} openResult={id=>{focusResult.current=true;setRecord(null);setJob(id);}} onCloseResult={()=>{setJob("");setRecord(null);}} restore={restore} footer={<HistoryCleanup allowSelected={false} key={job+"/"+(record?.status?.status || "")} service={service} job={job} state={record?.status?.status} onDeleted={message=>{setJob("");setRecord(null);setNotice(message);setHistoryRevision(v=>v+1);}}/>} renderResult={(id,close)=><div ref={resultRef} tabIndex={-1} aria-label="선택한 번역 작업"><button type="button" onClick={close}>결과 닫기</button><SavedGeneratorInputs id={id} service={service} statusCommand="translation-status"/><section ref={!record ? live.ref : undefined}><h2>번역 작업</h2><JobIdentifier id={id}/><RecordFolder key={id} service={service} id={id}/><button onClick={()=>setRevision(v=>v+1)}>상태 갱신</button>
        {statusCheckedAt && <p>마지막 조회 성공 · <time dateTime={statusCheckedAt.toISOString()}>{statusCheckedAt.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false})}</time></p>}
        {statusError && <p role="alert">번역 작업 상태를 불러오지 못했습니다. {statusError}{record?.id===id && " 아래 내용은 마지막으로 조회한 결과입니다."}{statusFailedAt && <> 조회 실패 시각 · <time dateTime={statusFailedAt.toISOString()}>{statusFailedAt.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false})}</time></>}</p>}
        {record?.id===id && <><p><JobStatus state={record.status.status}/> {record.status.error}</p><GenerationProgress jobId={id} job={{status:record.status.status}} live={live} supportsProgress={false}/><GeneratorJobControls showActions={false} key={id+"/"+record.status.status} service={service} id={id} state={record.status.status} refresh={()=>setRevision(value=>value+1)}/>{record.result && <TranslationResult key={id} job={id} text={record.result.text}/>}</>}
      </section></div>}/></div>
    </fieldset>
    {pending && <section ref={reviewRef} tabIndex={-1} className="translation-request-review" aria-label="번역 요청 확인"><h2>번역 요청 확인</h2><GpuQueueSummary/>
      <p>목표 언어 · {pending.target_language==="en"?"영어":"중국어 간체"}</p><h3>한국어 원문</h3><p className="translation-review-text">{pending.text}</p>
      <h3>확인할 용어</h3>{pending.glossary.length ? <ul>{pending.glossary.map((term,index)=><li key={index}>{term.source} → {term.target}</li>)}</ul> : <p>지정한 용어 없음</p>}
      <GenerationReviewActions busy={busy} onCancel={cancelReview} onConfirm={submit} disabledReason={!generationReady(model) ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : ""}/>
    </section>}
    <TranslationNotice message={notice} error={noticeError}/>
    {job && !pending && <button type="button" onClick={()=>openGeneratorHistory(historyRegion,job,()=>{})}>선택한 번역 작업 이력 보기</button>}
  </section>;
}
