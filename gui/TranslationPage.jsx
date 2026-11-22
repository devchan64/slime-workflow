import JobStatus from "./JobStatus.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
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
import TranslationEvidence from "./TranslationEvidence.jsx";
import TranslationResult from "./TranslationResult.jsx";
import SavedGeneratorInputs from "./SavedGeneratorInputs.jsx";
import {managementCommand} from "./managementCommand.js";
import {parseTranslationGlossary} from "./translationGlossary.mjs";
import {generationReady} from "./generationReady.mjs";

const service="prompt-translation";
const callHermes=(command,payload)=>managementCommand("hermes-agent","hermes-"+command,payload);

export default function TranslationPage({embedded=false}={}) {
  const query=new URLSearchParams(location.search);
  const [text,setText]=useState(""),[language,setLanguage]=useState("en"),[terms,setTerms]=useState("");
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState(""),[model,setModel]=useState(null);
  const [termsError,setTermsError]=useState("");
  const termsHelp=useId(),termsErrorId=useId(),termsRef=useRef(null),textRef=useRef(null),reviewRef=useRef(null);
  const resultRef=useRef(null),focusResult=useRef(false);
  const [job,setJob]=useState(embedded ? "" : query.get("job") || ""),[record,setRecord]=useState(null);
  const [revision,setRevision]=useState(0);
  const [historyRevision,setHistoryRevision]=useState(0);
  const sending=useRef(false);
  const live=useLiveRefresh(()=>setRevision(value=>value+1),Boolean(job) && (!record || ["queued","running"].includes(record.status?.status)));
  useEffect(()=>{if(!embedded)document.title="프롬프트 번역";},[embedded]);
  useEffect(()=>{if(pending)reviewRef.current?.focus();},[pending]);
  useEffect(()=>{if(focusResult.current && job && record?.id===job && resultRef.current){focusResult.current=false;resultRef.current.focus({preventScroll:true});resultRef.current.scrollIntoView({block:"start",inline:"nearest"});}},[job,record]);
  useEffect(()=>{
    if(!job)return;
    let active=true;
    async function read(){
      try{
        const next=await managementCommand(service,"translation-status",{id:job});
        if(!active)return;
        if(next.id!==job)throw new Error("작업 ID가 일치하지 않습니다.");
        setRecord(next);

      }catch(error){if(active)setNotice(error.message);}
    }
    read();return()=>{active=false;};
  },[job,revision]);
  function review(){
    try{
      const glossary=parseTranslationGlossary(terms);
      setPending({text,target_language:language,glossary});setTermsError("");setNotice("");
    }catch(error){setTermsError(error.message);termsRef.current?.focus();}
  }
  async function submit(){
    if(!pending || sending.current || !generationReady(model))return;
    sending.current=true;setBusy(true);
    try{
      const result=await managementCommand(service,"translation-submit",pending);
      if(typeof result?.id!=="string" || !result.id.trim())throw new Error("접수 ID를 확인할 수 없습니다.");
      setRecord(null);setJob(result.id);setNotice("번역 대기열에 등록했습니다.");
    }catch(error){setNotice(error.message+" · 이력을 조회해 접수 여부를 확인하세요."+(job ? " 아래 작업은 이전에 선택한 작업입니다." : ""));}
    finally{setPending(null);sending.current=false;setBusy(false);}
  }
  function restore(input){
    setText(input.text);setLanguage(input.target_language);
    setTerms((input.glossary||[]).map(term=>term.source+" => "+term.target).join("\n"));setTermsError("");
    setNotice("이력의 번역 입력을 불러왔습니다. 내용을 확인하거나 수정하세요.");
    requestAnimationFrame(()=>textRef.current?.focus());
  }
  return <section className={embedded ? "translation-page" : "translation-page translation-standalone"} style={embedded ? {minWidth:0} : undefined}>
    {!embedded && <a href={"/management/assistant/"+(query.has("session")?"?"+new URLSearchParams({session:query.get("session")}):"")}>헤르메스 대화</a>}
    <h1 className={embedded ? "embedded-page-title" : undefined}>프롬프트 번역</h1>
    <p>TranslateGemma 4B · ROCm BF16 · <a href="https://ai.google.dev/gemma/terms">Gemma 이용약관</a></p>
    <ModelReadiness service={service} onStatus={setModel}/><GeneratorChangelog generator={service}/>
    <fieldset disabled={Boolean(pending)}><label>한국어 원문 <textarea ref={textRef} value={text} onChange={e=>setText(e.target.value)}/></label>
      <label>목표 언어 <select value={language} onChange={e=>setLanguage(e.target.value)}><option value="en">영어</option><option value="zh-CN">중국어 간체</option></select></label>
      <label>확인할 용어 <textarea ref={termsRef} placeholder="원문 => 번역어" aria-describedby={termsError?`${termsHelp} ${termsErrorId}`:termsHelp} aria-invalid={Boolean(termsError)} value={terms} onChange={e=>{setTerms(e.target.value);setTermsError("");}}/></label>
      <small id={termsHelp}>선택 사항 · 한 줄에 하나씩 입력하세요. 예: 로봇 =&gt; robot</small>
      {termsError && <p id={termsErrorId} role="alert">{termsError}</p>}
      <p><PromptWordCount text={text} final/></p>
      <TranslationEvidence key={text} source={text} call={callHermes}/>
      <GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id){setJob("");setRecord(null);}setNotice(message);setHistoryRevision(v=>v+1);}} key={historyRevision} service={service} statusCommand="translation-status" externalResultId={job} restore={restore} inspectResult={item=>{focusResult.current=true;setJob(item.id);setRecord(item);}}/>
      <ActionButton reasons={[!text.trim() && "번역할 한국어 원문을 입력하세요."]} onClick={review}>번역 요청 검토</ActionButton>
    </fieldset>
    <HistoryCleanup allowSelected={false} key={job+"/"+(record?.status?.status || "")} service={service} job={job} state={record?.status?.status}
      onDeleted={message=>{setJob("");setRecord(null);setNotice(message);setHistoryRevision(v=>v+1);}}/>
    {pending && <section ref={reviewRef} tabIndex={-1} className="translation-request-review" aria-label="번역 요청 확인"><h2>번역 요청 확인</h2><GpuQueueSummary/>
      <p>목표 언어 · {pending.target_language==="en"?"영어":"중국어 간체"}</p><h3>한국어 원문</h3><p className="translation-review-text">{pending.text}</p>
      <h3>확인할 용어</h3>{pending.glossary.length ? <ul>{pending.glossary.map((term,index)=><li key={index}>{term.source} → {term.target}</li>)}</ul> : <p>지정한 용어 없음</p>}
      <GenerationReviewActions busy={busy} onCancel={()=>{setPending(null);requestAnimationFrame(()=>textRef.current?.focus());}} onConfirm={submit} disabledReason={!generationReady(model) ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : ""}/>
    </section>}
    <p role="status">{notice}</p>
    {job && <div ref={resultRef} tabIndex={-1} aria-label="선택한 번역 작업"><SavedGeneratorInputs id={job} service={service} statusCommand="translation-status"/><section ref={!record ? live.ref : undefined}><h2>번역 작업</h2><JobIdentifier id={job}/><RecordFolder key={job} service={service} id={job}/><button onClick={()=>setRevision(v=>v+1)}>상태 갱신</button>
      {record && <><p><JobStatus state={record.status.status}/> {record.status.error}</p><GenerationProgress job={{status:record.status.status}} live={live} supportsProgress={false}/></>}
      {record?.id===job && <GeneratorJobControls showActions={false} key={job+"/"+record.status.status} service={service} id={job}
        state={record.status.status} refresh={()=>setRevision(value=>value+1)}/>}
      {record?.result && <TranslationResult key={job} job={job} text={record.result.text}/>}
    </section></div>}
  </section>;
}
