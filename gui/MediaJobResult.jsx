import React, {useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import GenerationProgress from "./GenerationProgress.jsx";
import {useLiveRefresh} from "./LiveRefresh.jsx";

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

export default function MediaJobResult({service,id,kind="video",children,folderLink=false,onReuse}) {
  const [job,setJob]=useState(null);
  const [error,setError]=useState("");
  const [revision,refresh]=useState(0);
  const [folderNotice,setFolderNotice]=useState("");
  const live=useLiveRefresh(()=>refresh(value=>value+1),service==="wan22-fun-control" && (!job || ["queued","running"].includes(job.status)));
  async function openFolder(){
    try{
      const response=await fetch("/management/record-folder/open",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({route:"/"+service,id})});
      const result=await response.json();
      if(!response.ok)throw new Error(result.error || "폴더를 열 수 없습니다.");
      setFolderNotice(result.message);
    }catch(problem){setFolderNotice(problem.message);}
  }
  useEffect(()=>{
    let active=true,timer,lastActive=false;
    async function read() {
      try {
        const response=await managementCommand("hermes-agent",statusCommands[kind],{service,job_id:id});
        if(!active)return;
        if(response.service!==service || response.job_id!==id || !response.job)throw new Error("작업 결과가 요청과 일치하지 않습니다.");
        setJob(response.job);setError("");
        lastActive=["queued","running"].includes(response.job.status);
        if(service!=="wan22-fun-control" && lastActive)timer=setTimeout(read,5000);
      }catch(problem){if(active){setError(problem.message);if(service!=="wan22-fun-control" && lastActive)timer=setTimeout(read,5000);}}
    }
    read();
    return ()=>{active=false;clearTimeout(timer);};
  },[service,id,kind,revision]);
  return <section ref={service==="wan22-fun-control" && !job?live.ref:undefined} className="media-result-card" aria-label="작업 결과"><div className="media-result-heading"><div><strong>작업 결과</strong><h3>{id}</h3></div>{job && <span className={'media-result-status status-'+job.status}>{({completed:'완료',running:'실행 중',queued:'대기 중',failed:'실패',cancelled:'취소',canceled:'취소',paused:'중단',unknown:'확인 필요'})[job.status] || job.status}</span>}</div>
    {error && <p role="alert">{error}</p>}
    {job ? <>
      <p className="media-result-note" role="status">{job.note}</p>
      {service==="wan22-fun-control" && <GenerationProgress job={job} live={live}/>}
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
            <a className="media-result-link" href={job.video} target="_blank" rel="noopener">MP4 열기</a>
          </>}
        {service==="wan22-fun-control" && <SavedPoseVideo key={id} id={id}/>}
        {folderLink ? <><button type="button" onClick={openFolder}>결과 기록 폴더 열기</button><span role="status">{folderNotice}</span></> :
          <a href={job.download} download>{service==="dwpose"?"포즈 PNG·좌표 YAML 다운로드":"PNG 프레임 ZIP 다운로드"}</a>}
      </>}
      {(job.result_status==="unavailable" || job.file_observation==="unavailable") && <p>완료 기록의 결과 파일을 확인할 수 없습니다.</p>}
    </> : !error && <p>결과 조회 중…</p>}
    {children?.(job,()=>refresh(value=>value+1))}
    <div className="media-result-actions">{onReuse && job && <button type="button" onClick={onReuse}>입력 다시 사용</button>}<button type="button" onClick={()=>refresh(value=>value+1)}>결과 새로고침</button></div>
  </section>;
}
