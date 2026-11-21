import React, {useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";

const statusCommands={
  audio:"hermes-audio-source-status",
  video:"hermes-video-source-status",
  flux:"hermes-flux-source-status",
  image:"hermes-image-source-status",
};

export default function MediaJobResult({service,id,kind="video",children}) {
  const [job,setJob]=useState(null);
  const [error,setError]=useState("");
  const [revision,refresh]=useState(0);
  useEffect(()=>{
    let active=true,timer;
    async function read() {
      try {
        const response=await managementCommand("hermes-agent",statusCommands[kind],{service,job_id:id});
        if(!active)return;
        if(response.service!==service || response.job_id!==id || !response.job)throw new Error("작업 결과가 요청과 일치하지 않습니다.");
        setJob(response.job);setError("");
        if(["queued","running"].includes(response.job.status))timer=setTimeout(read,5000);
      }catch(problem){if(active){setError(problem.message);setJob(null);}}
    }
    read();
    return ()=>{active=false;clearTimeout(timer);};
  },[service,id,kind,revision]);
  return <section aria-label="작업 결과"><h3>{id}</h3>
    {error && <p role="alert">{error}</p>}
    {job ? <>
      <p role="status">{job.status} · {job.note}</p>
      {kind==="audio" && job.result_status==="available" && job.file_observation!=="unavailable" && <div>
        {(job.tracks || [{label:"생성 오디오",wav:job.audio}]).map(track=><section key={track.wav}>
          <strong>{track.label}</strong>
          <audio controls preload="metadata" src={track.wav} aria-label={track.label}/>
          <a href={track.wav} download>{track.label} WAV 다운로드</a>
          {track.mp3 && <a href={track.mp3} download>{track.label} MP3 다운로드</a>}
        </section>)}
      </div>}
      {["flux","image"].includes(kind) && job.result_status==="available" && <section>
        <img src={job.image} alt={service+" 생성 결과"} style={{maxWidth:"100%"}}/>
        <a href={job.image} download>결과 PNG 다운로드</a>
      </section>}
      {kind==="video" && job.result_status==="available" && <>
        {service==="dwpose" ? <img src={job.image} alt="DWPose 추출 결과" style={{maxWidth:"100%"}}/> :
          <video controls preload="metadata" src={job.video} poster={job.image} style={{maxWidth:"100%"}}/>}
        <a href={job.download} download>{service==="dwpose"?"포즈 PNG·좌표 YAML 다운로드":"결과 ZIP 다운로드"}</a>
      </>}
      {(job.result_status==="unavailable" || job.file_observation==="unavailable") && <p>완료 기록의 결과 파일을 확인할 수 없습니다.</p>}
    </> : !error && <p>결과 조회 중…</p>}
    {children?.(job,()=>refresh(value=>value+1))}
    <button onClick={()=>refresh(value=>value+1)}>결과 새로고침</button>
  </section>;
}
