import React,{useState} from "react";
import AnimateInputs from "./AnimateInputs.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import DownloadProgress from "./DownloadProgress.jsx";

const service="wan22-animate2";
async function readJob(id){
  const response=await fetch("/management/assistant/animate-input/"+encodeURIComponent(id)+"/request",{cache:"no-store"});
  if(!response.ok)throw new Error("저장된 입력을 확인할 수 없습니다.");
  return response.json();
}
export default function AnimatePage(){
  const query=new URLSearchParams(location.search);
  const [job,setJob]=useState(query.get("job") || "");
  const [saved,setSaved]=useState(null);
  const [revision,refresh]=useState(0);
  const [notice,setNotice]=useState("");
  function cleaned(message){setSaved(null);setJob("");refresh(n=>n+1);setNotice(message);}
  return <article><a href={"/management/assistant/"+(query.has("session")?"?"+new URLSearchParams({session:query.get("session")}):"")}>헤르메스 대화</a>
    <h1>Wan Animate-2 캐릭터 동작 전사</h1>
    <p>시스템 RAM과 GPU 메모리 부족으로 신규 생성과 재개를 보류합니다. 기존 작업의 참조와 결과 영상을 검수할 수 있습니다.</p>
    <GeneratorChangelog generator="wan22-animate2-generator"/><ModelReadiness service={service} manage/><DownloadProgress service={service}/>
    <AnimateInputs key={revision} saved={saved}/>
    <GeneratorHistory key={job+"-history-"+(saved?.id || "")} service={service} readJob={readJob}
      restore={(request,record)=>{setSaved(record);setJob(record.id);refresh(n=>n+1);}}/>
    {job && <MediaJobResult key={job} service={service} id={job}>
      {record=><HistoryCleanup key={record?.status} service={service} job={job} state={record?.status} onDeleted={cleaned}/>}
    </MediaJobResult>}
    {!job && <HistoryCleanup service={service} onDeleted={cleaned}/>}
    {notice && <p role="status">{notice}</p>}
  </article>;
}
