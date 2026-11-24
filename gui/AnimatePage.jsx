import React,{useRef,useState} from "react";
import AnimateInputs from "./AnimateInputs.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import GeneratorJobResult from "./GeneratorJobResult.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import DownloadProgress from "./DownloadProgress.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorSectionNavigation,{openGeneratorHistory} from "./GeneratorSectionNavigation.jsx";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import GeneratorUsage from "./GeneratorUsage.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";

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
  const query=new URLSearchParams(location.search);
  const session=embeddedSession || query.get("session") || "";
  const [job,setJob]=useState(embedded ? "" : query.get("job") || "");
  const [saved,setSaved]=useState(null);
  const [model,setModel]=useState(null),[loraModel,setLoraModel]=useState(null),[interacting,setInteracting]=useState(false);
  const [modelError,setModelError]=useState(""),[loraError,setLoraError]=useState("");
  const inputRef=useRef(null);
  const historyRef=useRef(null);
  const resultRef=useRef(null);
  const inputRevision=useRef(0),attachmentChecking=useRef(false);
  async function readHistory(id){
    const revisionAtStart=inputRevision.current,checkingAtStart=attachmentChecking.current;
    return {...await readJob(id),revisionAtStart,checkingAtStart};
  }
  const [historyRevision,refreshHistory]=useState(0);
  const [notice,setNotice]=useState("");
  function cleaned(message){setSaved(null);setJob("");refreshHistory(n=>n+1);setNotice(message);}
  function openResult(id){setJob(id);const details=historyRef.current?.querySelector('details.generator-history');if(details)details.open=true;}
  return <article className={"animate-page generator-page-common"+(embedded ? "" : " animate-standalone")}>
    <GeneratorPageIdentity service={service} embedded={embedded} session={session} showReturn changelogCard description="참조 이미지에 동작 영상의 움직임을 전사합니다."/>
    <GeneratorUsage generator={service}/>
    <GeneratorSectionNavigation inputRef={inputRef} historyRef={historyRef} resultRef={resultRef} resultReady={Boolean(job)} openOnNavigate/>
    <GeneratorSectionCard title="모델 준비" summary={modelError || loraError ? "상태 조회 실패 · 다시 확인하세요" : !model || !loraModel ? "상태 확인 중" : !model.ready ? "기본 모델 준비 필요" : !loraModel.ready ? "기본 모델 준비 완료 · LoRA 별도 준비" : "기본 모델·LoRA 준비 완료"}>
      <ModelReadiness session={session} service={service} manage onStatus={setModel} onError={setModelError}/><DownloadProgress service={service}/>
      <h3>선택 LoRA</h3><ModelReadiness session={session} service="wan22-animate2-lightx2v" manage onStatus={setLoraModel} onError={setLoraError}/><DownloadProgress service="wan22-animate2-lightx2v"/>
    </GeneratorSectionCard>
    <GeneratorSectionCard title="생성 입력" summary="참조 이미지와 동작 영상 · 16fps" defaultOpen>
      <section ref={inputRef} tabIndex={-1} aria-label="동작 전사 입력" onChangeCapture={()=>{inputRevision.current++;}}><AnimateInputs saved={saved} onSelectionStart={()=>{inputRevision.current++;}} onJob={openResult} session={session} model={model} loraModel={loraModel} onInteractionChange={setInteracting} onAttachmentCheckingChange={value=>{attachmentChecking.current=value;}}/></section>
    </GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={historyRevision+":"+job} onOpenResult={id=>openGeneratorHistory(historyRef,id,setJob)}/>
    <fieldset ref={historyRef} disabled={interacting}><GeneratorHistory card allowPriority onSelectedDeleted={(id,message)=>{if(job===id) cleaned(message); else setNotice(message);}} key={historyRevision} openResult={openResult} resultId={job} onCloseResult={()=>setJob("")} service={service} readJob={readHistory}
      restore={(request,record)=>{if(record.checkingAtStart || attachmentChecking.current || record.revisionAtStart!==inputRevision.current)throw new Error("첨부 확인 중이거나 조회 중 입력이 변경되어 적용하지 않았습니다. 확인 후 다시 시도하세요.");setSaved(record);requestAnimationFrame(()=>inputRef.current?.focus());}}
      footer={<HistoryCleanup allowSelected={false} service={service} onDeleted={cleaned}/>}
      renderResult={(id,close)=><section ref={resultRef} tabIndex={-1} aria-label="선택한 Animate-2 작업 결과"><button type="button" onClick={close}>결과 닫기</button><GeneratorJobResult selectionControls job={id} service={service} readJob={readJob} controls={false} onDeleted={cleaned}/></section>}/></fieldset>
    {notice && <p role="status">{notice}</p>}
  </article>;
}
