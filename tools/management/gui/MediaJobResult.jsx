import React, {useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";

const statusCommands={
  audio:"hermes-audio-source-status",
  video:"hermes-video-source-status",
  flux:"hermes-flux-source-status",
  image:"hermes-image-source-status",
};

function SeamlessComparison({id}){
  const [result,setResult]=useState(null),[error,setError]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    async function load(){
      try{
        const response=await fetch("/management/assistant/flux-seamless-comparison/"+encodeURIComponent(id),{signal:controller.signal});
        if(!response.ok)throw new Error("타일 비교 결과를 불러올 수 없습니다.");
        setResult(await response.json());
      }catch(problem){if(!controller.signal.aborted)setError(problem.message);}
    }
    load();return ()=>controller.abort();
  },[id]);
  if(error)return <p role="alert">{error}</p>;
  return result && <section><p>타일 생성 방식 · {result.method}</p>
    {result.images.map(item=><figure key={item.url}><figcaption>{item.label}</figcaption><img loading="lazy" src={item.url} alt={item.label} style={{maxWidth:"100%"}}/></figure>)}
    {!result.images.length && <p>저장된 비교 이미지가 없습니다.</p>}
  </section>;
}

function SavedPoseVideo({id}) {
  const [open,setOpen]=useState(false);
  const [failed,setFailed]=useState(false);
  return <details onToggle={event=>{setOpen(event.currentTarget.open);setFailed(false);}}>
    <summary>입력 포즈 영상과 비교</summary>
    {open && (failed ? <p role="status">이 작업의 포즈 MP4를 재생할 수 없습니다.</p> :
      <video aria-label="입력 포즈 영상" controls loop playsInline preload="metadata"
        src={"/management/assistant/fun-pose/"+encodeURIComponent(id)} onError={()=>setFailed(true)} style={{maxWidth:"100%"}}/>)}
  </details>;
}

export default function MediaJobResult({service,id,kind="video",children,folderLink=false}) {
  const [job,setJob]=useState(null);
  const [error,setError]=useState("");
  const [revision,refresh]=useState(0);
  const [folderNotice,setFolderNotice]=useState("");
  async function openFolder(){
    try{
      const response=await fetch("/management/record-folder/open",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({route:"/"+service,id})});
      const result=await response.json();
      if(!response.ok)throw new Error(result.error || "폴더를 열 수 없습니다.");
      setFolderNotice(result.message);
    }catch(problem){setFolderNotice(problem.message);}
  }
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
        {service==="flux-seamless" && <SeamlessComparison key={id+":"+revision} id={id}/>}
        <a href={job.image} download>결과 PNG 다운로드</a>
      </section>}
      {kind==="video" && job.result_status==="available" && <>
        {service==="dwpose" ? <img src={job.image} alt="DWPose 추출 결과" style={{maxWidth:"100%"}}/> :
          <>
            <video controls loop playsInline preload="metadata" src={job.video} poster={job.image} style={{maxWidth:"100%"}}/>
            <a href={job.video} target="_blank" rel="noopener">MP4 열기</a>
          </>}
        {service==="wan22-fun-control" && <SavedPoseVideo key={id} id={id}/>}
        {folderLink ? <><button type="button" onClick={openFolder}>결과 기록 폴더 열기</button><span role="status">{folderNotice}</span></> :
          <a href={job.download} download>{service==="dwpose"?"포즈 PNG·좌표 YAML 다운로드":"PNG 프레임 ZIP 다운로드"}</a>}
      </>}
      {(job.result_status==="unavailable" || job.file_observation==="unavailable") && <p>완료 기록의 결과 파일을 확인할 수 없습니다.</p>}
    </> : !error && <p>결과 조회 중…</p>}
    {children?.(job,()=>refresh(value=>value+1))}
    <button onClick={()=>refresh(value=>value+1)}>결과 새로고침</button>
  </section>;
}
