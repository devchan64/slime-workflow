import JobStatus from "./JobStatus.jsx";
import React, {useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import GenerationProgress from "./GenerationProgress.jsx";
import {validGenerationEstimate} from "./generationEstimate.mjs";
import {LiveRefreshControl,useLiveRefresh} from "./LiveRefresh.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import RecordFolder from "./RecordFolder.jsx";
import {liveJobStatus} from "./liveJobStatus.mjs";

const statusCommands={
  audio:"hermes-audio-source-status",
  video:"hermes-video-source-status",
  flux:"hermes-flux-source-status",
  image:"hermes-image-source-status",
  character:"hermes-character-source-status",
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

export function CircularComparisonImages({images}){
  return <section aria-label="순환 VAE 저장 결과"><h4>순환 VAE 저장 결과</h4>{images.map(item=><figure key={item.url}><figcaption>{item.label}</figcaption><img loading="lazy" src={item.url} alt={item.label} style={{maxWidth:"100%"}}/></figure>)}{!images.length && <p>저장된 비교 이미지가 없습니다.</p>}</section>;
}
function CircularComparison({id}){
  const [images,setImages]=useState(null),[error,setError]=useState("");
  useEffect(()=>{const controller=new AbortController();fetch("/management/assistant/qwen-circular-comparison/"+encodeURIComponent(id),{signal:controller.signal}).then(response=>{if(!response.ok)throw new Error("저장된 비교 결과를 불러올 수 없습니다.");return response.json();}).then(data=>{
    const prefix="/image-generation-21-circular/jobs/"+id+"/";
    if(!Array.isArray(data.images) || data.images.some(item=>typeof item.label!=="string" || !["result.png","tiled-preview.png","baseline.png","baseline-preview.png"].some(name=>item.url===prefix+name)))throw new Error("비교 결과 경로를 확인할 수 없습니다.");
    if(!controller.signal.aborted)setImages(data.images);
  }).catch(problem=>{if(!controller.signal.aborted)setError(problem.message);});return()=>controller.abort();},[id]);
  return error ? <p role="alert">{error}</p> : images && <CircularComparisonImages images={images}/>;
}

function SavedPoseVideo({id,resultVideo,resultPoster}) {
  const [open,setOpen]=useState(false);
  const [failed,setFailed]=useState(false);
  return <details onToggle={event=>{setOpen(event.currentTarget.open);setFailed(false);}}>
    <summary>입력 포즈 영상과 비교</summary>
    {open && <><p>각 영상을 개별 재생해 움직임을 비교할 수 있습니다.</p><div className="media-pose-comparison">
      <figure><figcaption>입력 포즈</figcaption>{failed ? <p role="status">이 작업의 포즈 MP4를 재생할 수 없습니다.</p> :
        <video aria-label="입력 포즈 영상" controls loop playsInline preload="metadata"
          src={"/management/assistant/fun-pose/"+encodeURIComponent(id)} onError={()=>setFailed(true)}/>}</figure>
      <figure><figcaption>생성 결과</figcaption><video aria-label="비교용 생성 결과 영상" controls loop playsInline preload="metadata" src={resultVideo} poster={resultPoster}/></figure>
    </div></>}
  </details>;
}

export function MediaResultError({error,stale}) {
  if(!error)return null;
  const missing=error.includes("영상 원본 작업 경로 오류") || error.includes("음악 작업 경로가 없거나 허용되지 않습니다");
  return <p role="alert">{missing ? "이 생성기에서 해당 작업을 찾지 못했습니다. 작업 ID와 이력을 확인해 주세요." : "작업 결과를 불러오지 못했습니다. 연결 상태를 확인하고 결과를 새로고침해 주세요."}{stale && " 아래 내용은 마지막으로 조회한 결과입니다."}</p>;
}

export default function MediaJobResult({service,id,kind="video",children,folderLink=false,onReuse,hideProgress=false,onStatusChange}) {
  const [job,setJob]=useState(null);
  const [error,setError]=useState("");
  const [checkedAt,setCheckedAt]=useState(null);
  const [revision,refresh]=useState(0),[loading,setLoading]=useState(true);
  useEffect(()=>{onStatusChange?.({id,status:job?.status || null,error});},[id,job?.status,error,onStatusChange]);
  const refreshRef=useRef(null),restoreRefreshFocus=useRef(false);
  useEffect(()=>{if(!loading && restoreRefreshFocus.current){restoreRefreshFocus.current=false;if(document.activeElement===document.body)refreshRef.current?.focus();}},[loading]);
  const live=useLiveRefresh(()=>refresh(value=>value+1),liveJobStatus(job));
  useEffect(()=>{setJob(null);setCheckedAt(null);setError("");},[service,id,kind]);
  useEffect(()=>{
    let active=true;
    setLoading(true);
    async function read() {
      try {
        const response=await managementCommand("hermes-agent",statusCommands[kind],kind==="character" ? {job_id:id} : {service,job_id:id});
        if(!active)return;
        if(response.service!==service || response.job_id!==id || !response.job)throw new Error("작업 결과가 요청과 일치하지 않습니다.");
        if(kind==="character" && response.job.image!=null){
          const prefix="/character-animation/files/"+id+"/";
          if(!response.job.image.startsWith(prefix) || !/^(down_left|down_right|up_left|up_right)\/frame-[0-9]{4}\/result\.png$/.test(response.job.image.slice(prefix.length)))throw new Error("프레임 경로를 확인할 수 없습니다.");
        }
        let estimate=validGenerationEstimate(response.job.estimate) ? response.job.estimate : null;
        if(kind==="audio" || kind==="flux"){
          try {
            const detail=await managementCommand(service,"status",{id});
            if((detail.id===id || (kind==="flux" && detail.id===undefined)) && detail.status===response.job.status && validGenerationEstimate(detail.estimate)) estimate=detail.estimate;
          } catch { /* Keep the observed result even if the optional estimate is unavailable. */ }
        }
        if(!active)return;
        setJob({...response.job,estimate});setCheckedAt(new Date());setError("");

      }catch(problem){if(active)setError(problem.message);}
      finally{if(active)setLoading(false);}
    }
    read();
    return ()=>{active=false;};
  },[service,id,kind,revision]);
  const directFolder=kind==="video" && service==="wan22-fun-control" && job?.result_status==="available";
  return <section ref={!job || hideProgress ? live.ref : undefined} className="media-result-card" aria-label="작업 결과"><div className="media-result-heading"><div><strong>작업 결과</strong></div>{job && <JobStatus state={job.status}/>}</div>
    {(!job || hideProgress) && <LiveRefreshControl live={live} label="결과 자동 갱신" inactiveReason="작업 종료로 중지"/>}
    {checkedAt && <p className="media-result-checked">마지막 조회 성공 · <time dateTime={checkedAt.toISOString()}>{checkedAt.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false})}</time></p>}
    <JobIdentifier id={id}/>
    {!directFolder && <RecordFolder key={service+"/"+id} service={service} id={id}/>}
    <MediaResultError error={error} stale={Boolean(job)}/>
    {loading && job && <p role="status">작업 결과를 다시 조회하고 있습니다.</p>}
    {job ? <>
      <p className="media-result-note" role="status">{job.note}</p>
      {!hideProgress && (["queued","running"].includes(job.status) ? <GenerationProgress job={job} live={live} supportsProgress={kind==="video"}/> : <details><summary>진행 정보 보기</summary><GenerationProgress job={job} supportsProgress={kind==="video"}/></details>)}
      {kind==="audio" && job.result_status==="available" && job.file_observation!=="unavailable" && <div className="media-audio-tracks">
        {(job.tracks || [{label:"생성 오디오",wav:job.audio}]).map(track=><section className="media-audio-track" key={track.wav}>
          <strong>{track.label}</strong>
          <audio controls preload="metadata" src={track.wav} aria-label={track.label}/>
          <div className="media-audio-downloads">
          <a href={track.wav} download>{track.label} WAV 다운로드</a>
          {track.mp3 && <a href={track.mp3} download>{track.label} MP3 다운로드</a>}
          </div>
        </section>)}
      </div>}
      {kind==="image" && service==="qwen-21-circular" && <CircularComparison key={id+":"+revision} id={id}/>}
      {kind==="character" && job.result_status==="available" && <figure><figcaption>마지막 완료 프레임</figcaption><img src={job.image} alt="마지막 완료 캐릭터 프레임" style={{maxWidth:"100%"}}/></figure>}
      {["flux","image"].includes(kind) && job.result_status==="available" && <section>
        <img src={job.image} alt={service+" 생성 결과"} style={{maxWidth:"100%"}}/>
        {service==="flux-seamless" && <SeamlessComparison key={id+":"+revision} id={id}/>}
        <a href={job.image} download>결과 PNG 다운로드</a>
      </section>}
      {kind==="video" && job.result_status==="available" && <>
        {service==="dwpose" ? <img src={job.image} alt="DWPose 추출 결과" style={{maxWidth:"100%"}}/> :
          <>
            <video aria-label="생성 결과 영상" controls loop playsInline preload="metadata" src={job.video} poster={job.image} style={{maxWidth:"100%"}}/>
            <a className="media-result-link" href={job.video} target="_blank" rel="noopener noreferrer">MP4 열기</a>
            {directFolder && <RecordFolder key={service+"/"+id} service={service} id={id} direct/>}
          </>}
        {service==="wan22-fun-control" && <SavedPoseVideo key={id} id={id} resultVideo={job.video} resultPoster={job.image}/>}
        {!directFolder && !folderLink && <a href={job.download} download>{service==="dwpose"?"포즈 PNG·좌표 YAML 다운로드":"PNG 프레임 ZIP 다운로드"}</a>}
      </>}
      {(job.result_status==="unavailable" || job.file_observation==="unavailable") && <p>완료 기록의 결과 파일을 확인할 수 없습니다.</p>}
    </> : !error && <p>결과 조회 중…</p>}
    {children?.(job,()=>refresh(value=>value+1))}
    <div className="media-result-actions">{onReuse && job && <button type="button" onClick={onReuse}>입력 다시 사용</button>}<button ref={refreshRef} type="button" disabled={loading} onClick={()=>{restoreRefreshFocus.current=true;refresh(value=>value+1);}}>{loading?"조회 중…":"결과 새로고침"}</button></div>
  </section>;
}
