import usePageTitle from "./usePageTitle.js";
import React,{useRef,useState} from "react";
import AnimateInputs from "./AnimateInputs.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import GeneratorJobResult from "./GeneratorJobResult.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import DownloadProgress from "./DownloadProgress.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";

const service="wan22-animate2";
async function readJob(id){
  const prefix="/management/assistant/animate-input/"+encodeURIComponent(id);
  const controller=new AbortController();let timedOut=false;
  const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
  try{
    const response=await fetch(prefix+"/request",{cache:"no-store",signal:controller.signal});
    if(!response.ok)throw new Error("저장된 입력을 확인할 수 없습니다.");
    let record;
    try{record=await response.json();}catch{throw new Error("저장된 입력 형식을 확인할 수 없습니다.");}
    if(!record || record.id!==id || !record.request || typeof record.request.prompt!=="string" ||
      ![record.request.frames,record.request.steps,record.request.seed].every(Number.isInteger) || !['none','lightx2v'].includes(record.request.lora_mode ?? 'none') ||
      record.reference!==prefix+"/reference" || record.motion!==prefix+"/motion")throw new Error("저장된 입력 형식을 확인할 수 없습니다.");
    return record;
  }catch(problem){if(timedOut)throw new Error("저장된 입력 조회 시간이 초과됐습니다.");throw problem;}
  finally{clearTimeout(timer);}
}
export default function AnimatePage({embedded=false,session:embeddedSession=""}={}){
  usePageTitle("Wan Animate-2 캐릭터 동작 전사",embedded);
  const query=new URLSearchParams(location.search);
  const session=embeddedSession || query.get("session") || "";
  const [job,setJob]=useState(embedded ? "" : query.get("job") || "");
  const [saved,setSaved]=useState(null);
  const [model,setModel]=useState(null),[loraModel,setLoraModel]=useState(null),[interacting,setInteracting]=useState(false);
  const inputRef=useRef(null);
  const historyRef=useRef(null);
  const inputRevision=useRef(0);
  async function readHistory(id){
    const revisionAtStart=inputRevision.current;
    return {...await readJob(id),revisionAtStart};
  }
  const [historyRevision,refreshHistory]=useState(0);
  const [notice,setNotice]=useState("");
  function cleaned(message){setSaved(null);setJob("");refreshHistory(n=>n+1);setNotice(message);}
  function openResult(id){setJob(id);const details=historyRef.current?.querySelector('details.generator-history');if(details)details.open=true;}
  return <article className={embedded ? "animate-page" : "animate-page animate-standalone"}><a href={"/management/assistant/"+(query.has("session")?"?"+new URLSearchParams({session:query.get("session")}):"")}>헤르메스 대화</a>
    <h1 className={embedded ? "embedded-page-title" : undefined}>Wan Animate-2 캐릭터 동작 전사</h1>
    <p>공식 Base 모델로 동작을 전사합니다. 시스템 메모리와 GPU 메모리가 부족하면 작업이 실패할 수 있습니다.</p>
    <GeneratorChangelog generator="wan22-animate2-generator"/><ModelReadiness service={service} manage onStatus={setModel}/><DownloadProgress service={service}/>
    <h2>선택 LoRA 준비</h2><ModelReadiness service="wan22-animate2-lightx2v" manage onStatus={setLoraModel}/><DownloadProgress service="wan22-animate2-lightx2v"/>
    <section ref={inputRef} tabIndex={-1} aria-label="동작 전사 입력" onChangeCapture={()=>{inputRevision.current++;}}><AnimateInputs saved={saved} onSelectionStart={()=>{inputRevision.current++;}} onJob={openResult} session={session} model={model} loraModel={loraModel} onInteractionChange={setInteracting}/></section>
    <ActiveGeneratorProgress service={service} revision={historyRevision+":"+job} onOpenResult={openResult}/>
    <fieldset ref={historyRef} disabled={interacting}><GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id) cleaned(message); else setNotice(message);}} key={historyRevision} openResult={openResult} resultId={job} onCloseResult={()=>setJob("")} service={service} readJob={readHistory}
      restore={(request,record)=>{if(record.revisionAtStart!==inputRevision.current)throw new Error("입력 조회 중 작성 내용이나 첨부가 변경되어 적용하지 않았습니다.");setSaved(record);requestAnimationFrame(()=>inputRef.current?.focus());}}
      renderResult={(id,close)=><section aria-label="선택한 Animate-2 작업 결과"><button type="button" onClick={close}>결과 닫기</button><GeneratorJobResult selectionControls job={id} service={service} readJob={readJob} controls={false} onDeleted={cleaned}/></section>}/></fieldset>
    <GeneratorJobResult selectionControls job="" service={service} onDeleted={cleaned}/>
    {notice && <p role="status">{notice}</p>}
  </article>;
}
