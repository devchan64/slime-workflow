import usePageTitle from "./usePageTitle.js";
import React,{useRef,useState} from "react";
import AnimateInputs from "./AnimateInputs.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import GeneratorJobResult from "./GeneratorJobResult.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import DownloadProgress from "./DownloadProgress.jsx";

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
      ![record.request.frames,record.request.steps,record.request.seed].every(Number.isInteger) ||
      record.reference!==prefix+"/reference" || record.motion!==prefix+"/motion")throw new Error("저장된 입력 형식을 확인할 수 없습니다.");
    return record;
  }catch(problem){if(timedOut)throw new Error("저장된 입력 조회 시간이 초과됐습니다.");throw problem;}
  finally{clearTimeout(timer);}
}
export default function AnimatePage({embedded=false}={}){
  usePageTitle("Wan Animate-2 캐릭터 동작 전사",embedded);
  const query=new URLSearchParams(location.search);
  const [job,setJob]=useState(embedded ? "" : query.get("job") || "");
  const [saved,setSaved]=useState(null);
  const inputRef=useRef(null);
  const [historyRevision,refreshHistory]=useState(0);
  const [notice,setNotice]=useState("");
  function cleaned(message){setSaved(null);setJob("");refreshHistory(n=>n+1);setNotice(message);}
  return <article className={embedded ? "animate-page" : "animate-page animate-standalone"}><a href={"/management/assistant/"+(query.has("session")?"?"+new URLSearchParams({session:query.get("session")}):"")}>헤르메스 대화</a>
    <h1 className={embedded ? "embedded-page-title" : undefined}>Wan Animate-2 캐릭터 동작 전사</h1>
    <p>시스템 RAM과 GPU 메모리 부족으로 신규 생성과 재개를 보류합니다. 기존 작업의 참조와 결과 영상을 검수할 수 있습니다.</p>
    <GeneratorChangelog generator="wan22-animate2-generator"/><ModelReadiness service={service} manage/><DownloadProgress service={service}/>
    <section ref={inputRef} tabIndex={-1} aria-label="동작 전사 입력"><AnimateInputs saved={saved}/></section>
    <GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id) cleaned(message); else setNotice(message);}} key={historyRevision} openResult={setJob} resultId={job} onCloseResult={()=>setJob("")} service={service} readJob={readJob}
      restore={(request,record)=>{setSaved(record);requestAnimationFrame(()=>inputRef.current?.focus());}}
      renderResult={(id,close)=><section aria-label="선택한 Animate-2 작업 결과"><button type="button" onClick={close}>결과 닫기</button><GeneratorJobResult selectionControls job={id} service={service} readJob={readJob} controls={false} onDeleted={cleaned}/></section>}/>
    <GeneratorJobResult selectionControls job="" service={service} onDeleted={cleaned}/>
    {notice && <p role="status">{notice}</p>}
  </article>;
}
