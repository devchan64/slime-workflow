import KimodoMultiviewReport from "./KimodoMultiviewReport.jsx";
import KimodoGeneration from "./KimodoGeneration.jsx";
import React, {useRef,useState} from "react";
import ModelReadiness from "./ModelReadiness.jsx";
import DownloadProgress from "./DownloadProgress.jsx";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorSectionNavigation from "./GeneratorSectionNavigation.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import KimodoFrames from "./KimodoFrames.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";

export default function KimodoPage({embedded=false,session:embeddedSession="",initialInputs=null,onChoose}={}){
  const params=new URLSearchParams(location.search);
  const session=embedded ? embeddedSession : params.get("session") || "";
  const [selectedJob,setSelectedJob]=useState(embedded ? "" : params.get("job") || "");
  const resultRef=useRef(null);
  const historyRef=useRef(null);
  const generationRef=useRef(null);
  const [restoreJob,setRestoreJob]=useState(embedded ? "" : params.get("restore") || "");
  const [historyRevision,setHistoryRevision]=useState(0);
  const [restoreRevision,setRestoreRevision]=useState(0);
  const [notice,setNotice]=useState("");
  async function readJob(id){
    const response=await fetch("/management/assistant/kimodo-input/"+encodeURIComponent(id),{cache:"no-store"});
    if(!response.ok)throw new Error("저장된 Kimodo 입력을 확인할 수 없습니다.");
    const saved=await response.json();
    if(!saved || !saved.inputs)throw new Error("저장된 Kimodo 입력을 확인할 수 없습니다.");
    return {id,request:saved.inputs};
  }
  function cleaned(message){setSelectedJob("");setNotice(message);setHistoryRevision(value=>value+1);}
  const conversation="/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"");
  function choose(label,value){
    if(embedded && onChoose){onChoose(label,value);return;}
    const key="hermes-draft-"+session;
    sessionStorage.setItem(key,[sessionStorage.getItem(key),label+" "+value].filter(Boolean).join("\n"));
    location.assign(conversation);
  }
  return <main className={"single-generator-shell"+(embedded ? "" : " generator-page-standalone-shell")}><article className="single-generator-page generator-page-common"><GeneratorPageIdentity service="kimodo" embedded={embedded} session={session}/><GeneratorSectionNavigation inputRef={generationRef} historyRef={historyRef} resultRef={resultRef} resultReady={Boolean(selectedJob)}/>
    {embedded ? <details><summary>모델 준비 및 다운로드</summary><ModelReadiness service="kimodo" manage/><DownloadProgress service="kimodo"/></details> : <><ModelReadiness service="kimodo" manage/><DownloadProgress service="kimodo"/></>}
    <section className={embedded ? undefined : "kimodo-standalone-form"} ref={generationRef} tabIndex={-1} aria-label="Kimodo 생성 입력"><KimodoGeneration key={(restoreJob || "new")+"/"+restoreRevision} session={session} restoreJob={restoreJob} initialInputs={restoreJob ? null : initialInputs} choose={choose}/></section>
    <KimodoMultiviewReport/>
    <div ref={historyRef}><GeneratorHistory key={historyRevision} service="kimodo" allowPriority readJob={readJob} externalResultId={selectedJob}
      openResult={id=>{setSelectedJob(id);requestAnimationFrame(()=>resultRef.current?.focus());}} restore={(_request,record)=>{setRestoreJob(record.id);setRestoreRevision(value=>value+1);setNotice("");requestAnimationFrame(()=>generationRef.current?.focus());}}
      onSelectedDeleted={(id,message)=>{if(selectedJob===id)setSelectedJob("");setNotice(message);setHistoryRevision(value=>value+1);}}/></div>
    {notice && <p role="status">{notice}</p>}
    {selectedJob ? <section ref={resultRef} tabIndex={-1} aria-label="선택한 Kimodo 작업 결과"><button type="button" onClick={()=>{const closedJob=selectedJob;setSelectedJob("");requestAnimationFrame(()=>{const history=historyRef.current;const items=history?.querySelectorAll('details.generator-history[open] .generator-history-item') || [];const item=Array.from(items).find(element=>element.dataset.historyId===closedJob);const target=item?.querySelector('.generator-history-select') || history?.querySelector('summary');target?.focus();});}}>결과 닫고 이력으로</button><button type="button" onClick={()=>choose("kimodo 작업",selectedJob)}>선택 작업을 대화 입력에 추가</button><KimodoFrames key={selectedJob} id={selectedJob} choose={choose} onDeleted={cleaned} selectionControls/></section> :
      <HistoryCleanup service="kimodo" allowSelected={false} onDeleted={cleaned}/>}
  </article></main>;
}
