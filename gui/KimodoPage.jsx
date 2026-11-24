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
import SavedGeneratorInputs from "./SavedGeneratorInputs.jsx";

export default function KimodoPage({embedded=false,session:embeddedSession="",initialInputs=null,onChoose}={}){
  const params=new URLSearchParams(location.search);
  const session=embedded ? embeddedSession : params.get("session") || "";
  const [selectedJob,setSelectedJob]=useState(embedded ? "" : params.get("job") || "");
  const resultRef=useRef(null),focusResult=useRef(false);
  const historyRef=useRef(null);
  const generationRef=useRef(null);
  const inputRevision=useRef(0),imageChecking=useRef(false);
  function trackInputAction(event){
    const button=event.target.closest("button");
    if(button && !["키프레임 배치 편집","배치 편집 닫기","신체 비율 예시 조회","접수 상태 확인"].includes(button.textContent.trim()))inputRevision.current++;
  }
  const [restoreJob,setRestoreJob]=useState(embedded ? "" : params.get("restore") || "");
  const [historyRevision,setHistoryRevision]=useState(0);
  const [restoreRevision,setRestoreRevision]=useState(0);
  const [notice,setNotice]=useState("");
  async function readJob(id){
    const revisionAtStart=inputRevision.current,checkingAtStart=imageChecking.current;
    const controller=new AbortController();let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
    const response=await fetch("/management/assistant/kimodo-input/"+encodeURIComponent(id),{cache:"no-store",signal:controller.signal});
    if(!response.ok)throw new Error("저장된 Kimodo 입력을 확인할 수 없습니다.");
    const saved=await response.json();
    if(!saved || !saved.inputs)throw new Error("저장된 Kimodo 입력을 확인할 수 없습니다.");
    return {id,request:saved.inputs,revisionAtStart,checkingAtStart};
    }catch(error){if(timedOut)throw new Error("저장 입력 조회 시간이 초과됐습니다. 다시 조회하세요.");throw error;}
    finally{clearTimeout(timeout);}
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
    <section className={embedded ? undefined : "kimodo-standalone-form"} ref={generationRef} tabIndex={-1} aria-label="Kimodo 생성 입력" onChangeCapture={()=>{inputRevision.current++;}} onClickCapture={trackInputAction}><KimodoGeneration session={session} restoreJob={restoreJob} restoreRevision={restoreRevision} initialInputs={restoreJob ? null : initialInputs} choose={choose} onInputChange={()=>{inputRevision.current++;}} onImageCheckingChange={value=>{imageChecking.current=value;}}/></section>
    <KimodoMultiviewReport/>
    <div ref={historyRef}><GeneratorHistory key={historyRevision} service="kimodo" allowPriority readJob={readJob} resultId={selectedJob}
      openResult={id=>{focusResult.current=true;setSelectedJob(id);}} onCloseResult={()=>setSelectedJob("")} restore={(_request,record)=>{if(record.checkingAtStart || imageChecking.current || record.revisionAtStart!==inputRevision.current)throw new Error("이미지 확인 중이거나 조회 중 생성 폼이 변경되어 적용하지 않았습니다. 확인 후 다시 시도하세요.");setRestoreJob(record.id);setRestoreRevision(value=>value+1);setNotice("");requestAnimationFrame(()=>generationRef.current?.focus());}}
      onSelectedDeleted={(id,message)=>{if(selectedJob===id)setSelectedJob("");setNotice(message);setHistoryRevision(value=>value+1);}}
      renderResult={(id,close)=><section ref={node=>{resultRef.current=node;if(node && focusResult.current){focusResult.current=false;requestAnimationFrame(()=>{if(node.isConnected && document.activeElement===document.body)node.focus();});}}} tabIndex={-1} aria-label="선택한 Kimodo 작업 결과"><button type="button" onClick={close}>결과 닫고 이력으로</button><button type="button" onClick={()=>choose("kimodo 작업",id)}>선택 작업을 대화 입력에 추가</button><SavedGeneratorInputs id={id} service="kimodo" readJob={readJob}/><KimodoFrames key={id} id={id} choose={choose} onDeleted={cleaned} selectionControls/></section>}/></div>
    {notice && <p role="status">{notice}</p>}
    <HistoryCleanup service="kimodo" allowSelected={false} onDeleted={cleaned}/>
  </article></main>;
}
