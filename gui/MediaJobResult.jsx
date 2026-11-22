import JobStatus from "./JobStatus.jsx";
import React, {useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import GenerationProgress from "./GenerationProgress.jsx";
import {validGenerationEstimate} from "./generationEstimate.mjs";
import {validMediaResultDetails} from "./mediaResultValidation.mjs";
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

function ComparisonFigure({item}){
  const [failed,setFailed]=useState(false),[revision,retry]=useState(0);
  const imageRef=useRef(null),buttonRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>{if(restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)(failed ? buttonRef : imageRef).current?.focus();}},[failed,revision]);
  return <figure><figcaption>{item.label}</figcaption>{failed ? <div role="alert"><p>비교 이미지를 불러오지 못했습니다.</p><button ref={buttonRef} type="button" aria-label={item.label+" 다시 불러오기"} onClick={()=>{restoreFocus.current=document.activeElement===buttonRef.current;setFailed(false);retry(value=>value+1);}}>이미지 다시 불러오기</button></div> : <img ref={imageRef} tabIndex={-1} key={revision} loading="lazy" src={item.url} alt={item.label} style={{maxWidth:"100%"}} onError={()=>{restoreFocus.current=document.activeElement===imageRef.current;setFailed(true);}}/>}</figure>;
}

function SeamlessComparison({id}){
  const [result,setResult]=useState(null),[error,setError]=useState(""),[revision,retry]=useState(0),[loading,setLoading]=useState(true);
  const retryRef=useRef(null),resultRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>{if(!loading && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)(error ? retryRef : resultRef).current?.focus();}},[loading,error]);
  useEffect(()=>{
    const controller=new AbortController();let active=true,timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},15000);
    async function load(){
      setLoading(true);setError("");
      try{
        const value=await untilAborted((async()=>{const response=await fetch("/management/assistant/flux-seamless-comparison/"+encodeURIComponent(id),{signal:controller.signal});if(!response.ok)throw new Error("타일 비교 결과를 불러올 수 없습니다.");return response.json();})(),controller.signal);
        const prefix="/flux-seamless-generator/jobs/"+id+"/";
        if(!value || typeof value.method!=="string" || !Array.isArray(value.images) || value.images.some(item=>!item || typeof item.label!=="string" || !["tiled-preview.png","raw-result.png","blend-preview.png"].some(name=>item.url===prefix+name)))throw new Error("타일 비교 결과 형식을 확인할 수 없습니다.");
        if(active && !controller.signal.aborted)setResult(value);
      }catch(problem){if(active)setError(timedOut?"타일 비교 조회 시간이 초과됐습니다.":problem.message || "타일 비교 결과를 불러올 수 없습니다.");}
      finally{clearTimeout(timer);if(active)setLoading(false);}
    }
    load();return ()=>{active=false;clearTimeout(timer);controller.abort();};
  },[id,revision]);
  if(error)return <div role="alert"><p>{error}</p><button ref={retryRef} type="button" onClick={()=>{restoreFocus.current=document.activeElement===retryRef.current;retry(value=>value+1);}}>타일 비교 다시 조회</button></div>;
  if(loading)return <p role="status">타일 비교 결과 조회 중…</p>;
  return result && <section ref={resultRef} tabIndex={-1} aria-label="타일 비교 결과"><p>타일 생성 방식 · {result.method}</p>
    {result.images.map(item=><ComparisonFigure key={item.url} item={item}/>)}
    {!result.images.length && <p>저장된 비교 이미지가 없습니다.</p>}
  </section>;
}

export function CircularComparisonImages({images}){
  return <section aria-label="순환 VAE 저장 결과"><h4>순환 VAE 저장 결과</h4>{images.map(item=><ComparisonFigure key={item.url} item={item}/>)}{!images.length && <p>저장된 비교 이미지가 없습니다.</p>}</section>;
}
function CircularComparison({id}){
  const [images,setImages]=useState(null),[error,setError]=useState(""),[revision,retry]=useState(0),[loading,setLoading]=useState(true);
  const retryRef=useRef(null),resultRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>{if(!loading && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)(error ? retryRef : resultRef).current?.focus();}},[loading,error]);
  useEffect(()=>{
    const controller=new AbortController();let active=true,timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},15000);
    async function load(){
      setLoading(true);setError("");
      try{
        const data=await untilAborted((async()=>{const response=await fetch("/management/assistant/qwen-circular-comparison/"+encodeURIComponent(id),{signal:controller.signal});if(!response.ok)throw new Error("저장된 비교 결과를 불러올 수 없습니다.");return response.json();})(),controller.signal);
        const prefix="/image-generation-21-circular/jobs/"+id+"/";
        if(!Array.isArray(data?.images) || data.images.some(item=>!item || typeof item.label!=="string" || !["result.png","tiled-preview.png","baseline.png","baseline-preview.png"].some(name=>item.url===prefix+name)))throw new Error("비교 결과 경로를 확인할 수 없습니다.");
        if(active && !controller.signal.aborted)setImages(data.images);
      }catch(problem){if(active)setError(timedOut?"순환 VAE 비교 조회 시간이 초과됐습니다.":problem.message || "저장된 비교 결과를 불러올 수 없습니다.");}
      finally{clearTimeout(timer);if(active)setLoading(false);}
    }
    load();return()=>{active=false;clearTimeout(timer);controller.abort();};
  },[id,revision]);
  if(error)return <div role="alert"><p>{error}</p><button ref={retryRef} type="button" onClick={()=>{restoreFocus.current=document.activeElement===retryRef.current;retry(value=>value+1);}}>순환 VAE 비교 다시 조회</button></div>;
  return loading ? <p role="status">순환 VAE 비교 결과 조회 중…</p> : images && <div ref={resultRef} tabIndex={-1} aria-label="순환 VAE 비교 결과"><CircularComparisonImages images={images}/></div>;
}

function SavedPoseVideo({id,resultVideo,resultPoster}) {
  const [open,setOpen]=useState(false);
  const [failed,setFailed]=useState(false),[revision,retry]=useState(0);
  const videoRef=useRef(null),retryRef=useRef(null),restoreFocus=useRef(false);
  const [outputFailed,setOutputFailed]=useState(false),[outputRevision,retryOutput]=useState(0);
  const outputRef=useRef(null),outputRetryRef=useRef(null),restoreOutputFocus=useRef(false);
  useEffect(()=>{if(restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)(failed ? retryRef : videoRef).current?.focus();}},[failed,revision]);
  useEffect(()=>{if(restoreOutputFocus.current){restoreOutputFocus.current=false;if(document.activeElement===document.body)(outputFailed ? outputRetryRef : outputRef).current?.focus();}},[outputFailed,outputRevision]);
  return <details onToggle={event=>{setOpen(event.currentTarget.open);setFailed(false);setOutputFailed(false);}}>
    <summary>입력 포즈 영상과 비교</summary>
    {open && <><p>각 영상을 개별 재생해 움직임을 비교할 수 있습니다.</p><div className="media-pose-comparison">
      <figure><figcaption>입력 포즈</figcaption>{failed ? <div role="alert"><p>이 작업의 포즈 MP4를 재생할 수 없습니다.</p><button ref={retryRef} type="button" onClick={()=>{restoreFocus.current=document.activeElement===retryRef.current;setFailed(false);retry(value=>value+1);}}>입력 포즈 다시 불러오기</button></div> :
        <video ref={videoRef} key={revision} aria-label="입력 포즈 영상" controls loop playsInline preload="metadata"
          src={"/management/assistant/fun-pose/"+encodeURIComponent(id)} onError={()=>{restoreFocus.current=document.activeElement===videoRef.current;setFailed(true);}}/>}</figure>
      <figure><figcaption>생성 결과</figcaption>{outputFailed ? <div role="alert"><p>생성 결과 영상을 불러오지 못했습니다.</p><button ref={outputRetryRef} type="button" onClick={()=>{restoreOutputFocus.current=document.activeElement===outputRetryRef.current;setOutputFailed(false);retryOutput(value=>value+1);}}>비교 영상 다시 불러오기</button></div> : <video ref={outputRef} key={outputRevision} aria-label="비교용 생성 결과 영상" controls loop playsInline preload="metadata" src={resultVideo} poster={resultPoster} onError={()=>{restoreOutputFocus.current=document.activeElement===outputRef.current;setOutputFailed(true);}}/>}</figure>
    </div></>}
  </details>;
}

export function MediaResultError({error,stale}) {
  if(!error)return null;
  const missing=error.includes("영상 원본 작업 경로 오류") || error.includes("음악 작업 경로가 없거나 허용되지 않습니다");
  return <p role="alert">{missing ? "이 생성기에서 해당 작업을 찾지 못했습니다. 작업 ID와 이력을 확인해 주세요." : error.includes("시간이 초과") ? "작업 결과 조회 시간이 초과됐습니다. 다시 조회해 주세요." : error.includes("형식") || error.includes("요청과 일치") ? "작업 결과의 내용을 확인하지 못했습니다. 결과를 다시 조회해 주세요." : "작업 결과를 불러오지 못했습니다. 연결 상태를 확인하고 결과를 새로고침해 주세요."}{stale && " 아래 내용은 마지막으로 조회한 결과입니다."}</p>;
}

function AudioTrack({track}) {
  const [failed,setFailed]=useState(false),[revision,retry]=useState(0);
  const audioRef=useRef(null),retryRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>{if(restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)(failed ? retryRef : audioRef).current?.focus();}},[failed,revision]);
  return <section className="media-audio-track"><strong>{track.label}</strong>
    {failed ? <div role="alert"><p>오디오를 불러오지 못했습니다. 파일 상태를 확인하세요.</p><button ref={retryRef} type="button" aria-label={track.label+" 다시 불러오기"} onClick={()=>{restoreFocus.current=document.activeElement===retryRef.current;setFailed(false);retry(value=>value+1);}}>오디오 다시 불러오기</button></div> : <audio ref={audioRef} key={revision} controls preload="metadata" src={track.wav} aria-label={track.label} onError={()=>{restoreFocus.current=document.activeElement===audioRef.current;setFailed(true);}}/>}
    <div className="media-audio-downloads"><a href={track.wav} download>{track.label} WAV 다운로드</a>{track.mp3 && <a href={track.mp3} download>{track.label} MP3 다운로드</a>}</div>
  </section>;
}

export default function MediaJobResult({service,id,kind="video",children,folderLink=false,onReuse,hideProgress=false,onStatusChange,inGenerator=false}) {
  const [job,setJob]=useState(null);
  const [error,setError]=useState("");
  const [checkedAt,setCheckedAt]=useState(null);
  const [attemptedAt,setAttemptedAt]=useState(null);
  const [revision,refresh]=useState(0),[mediaRevision,retryMedia]=useState(0),[loading,setLoading]=useState(true);
  const [imageError,setImageError]=useState(false);
  const [videoError,setVideoError]=useState(false);
  const videoRef=useRef(null),videoRetryRef=useRef(null);
  const imageRef=useRef(null),imageRetryRef=useRef(null),restoreImageFocus=useRef(false);
  useEffect(()=>{if(restoreImageFocus.current){restoreImageFocus.current=false;if(document.activeElement===document.body)(imageError ? imageRetryRef : imageRef).current?.focus();}},[imageError,mediaRevision]);
  useEffect(()=>setImageError(false),[service,id,kind,mediaRevision,job?.image]);
  useEffect(()=>setVideoError(false),[service,id,kind,mediaRevision,job?.video]);
  useEffect(()=>{onStatusChange?.({id,status:job?.status || null,error});},[id,job?.status,error,onStatusChange]);
  const refreshRef=useRef(null),restoreRefreshFocus=useRef(false);
  useEffect(()=>{if(!loading && restoreRefreshFocus.current){restoreRefreshFocus.current=false;if(document.activeElement===document.body)refreshRef.current?.focus();}},[loading]);
  const live=useLiveRefresh(()=>refresh(value=>value+1),liveJobStatus(job));
  useEffect(()=>{setJob(null);setCheckedAt(null);setAttemptedAt(null);setError("");},[service,id,kind]);
  useEffect(()=>{
    let active=true,deadline;const controller=new AbortController();
    if(document.activeElement===refreshRef.current)restoreRefreshFocus.current=true;
    setLoading(true);
    deadline=setTimeout(()=>{controller.abort();if(active){setError("작업 결과 조회 시간이 초과됐습니다.");setAttemptedAt(new Date());setLoading(false);}},25000);
    async function read() {
      try {
        const response=await untilAborted(managementCommand("hermes-agent",statusCommands[kind],kind==="character" ? {job_id:id} : {service,job_id:id},{signal:controller.signal}),controller.signal);
        if(!active || controller.signal.aborted)return;
        if(response.service!==service || response.job_id!==id || !response.job || typeof response.job!=="object" || Array.isArray(response.job) || typeof response.job.status!=="string" || !response.job.status.trim() || !["available","unavailable","not_ready","partial"].includes(response.job.result_status))throw new Error("작업 결과가 요청과 일치하지 않습니다.");
        if(!validMediaResultDetails(response.job,kind,service))throw new Error("작업 결과 형식을 확인할 수 없습니다.");
        if(kind==="character" && response.job.image!=null){
          const prefix="/character-animation/files/"+id+"/";
          if(!response.job.image.startsWith(prefix) || !/^(down_left|down_right|up_left|up_right)\/frame-[0-9]{4}\/result\.png$/.test(response.job.image.slice(prefix.length)))throw new Error("프레임 경로를 확인할 수 없습니다.");
        }
        let estimate=validGenerationEstimate(response.job.estimate) ? response.job.estimate : null;
        setJob({...response.job,estimate});setCheckedAt(new Date());setError("");
        if(kind==="audio" || kind==="flux"){
          const optionalController=new AbortController();let optionalDeadline;
          const abortOptional=()=>optionalController.abort();
          controller.signal.addEventListener("abort",abortOptional,{once:true});
          try {
            const detail=await Promise.race([managementCommand(service,"status",{id},{signal:optionalController.signal}),new Promise(resolve=>{optionalDeadline=setTimeout(()=>{resolve(null);optionalController.abort();},5000);})]);
            if(detail && (detail.id===id || (kind==="flux" && detail.id===undefined)) && detail.status===response.job.status && validGenerationEstimate(detail.estimate)) estimate=detail.estimate;
          } catch { /* Keep the observed result even if the optional estimate is unavailable. */ }
          finally{clearTimeout(optionalDeadline);controller.signal.removeEventListener("abort",abortOptional);}
        }
        if(!active || controller.signal.aborted)return;
        setJob({...response.job,estimate});

      }catch(problem){if(active && !controller.signal.aborted)setError(problem.message);}
      finally{clearTimeout(deadline);if(active && !controller.signal.aborted){setAttemptedAt(new Date());setLoading(false);}}
    }
    read();
    return ()=>{active=false;clearTimeout(deadline);controller.abort();};
  },[service,id,kind,revision]);
  const directFolder=kind==="video" && service==="wan22-fun-control" && job?.result_status==="available";
  function renderResultImage(alt,className){
    return imageError ? <div role="alert"><p>결과 이미지를 불러오지 못했습니다. 파일 상태를 확인하세요.</p><button ref={imageRetryRef} type="button" onClick={()=>{restoreImageFocus.current=document.activeElement===imageRetryRef.current;setImageError(false);retryMedia(value=>value+1);}}>이미지 다시 불러오기</button></div> : <img ref={imageRef} tabIndex={-1} className={className} key={mediaRevision} src={job.image} alt={alt} onError={()=>{restoreImageFocus.current=document.activeElement===imageRef.current;setImageError(true);}}/>;
  }
  return <section ref={!job || hideProgress ? live.ref : undefined} className="media-result-card" aria-label="작업 결과"><div className="media-result-heading"><div><strong>작업 결과</strong></div>{job && <JobStatus state={job.status}/>}</div>
    {(!job || hideProgress) && <LiveRefreshControl live={live} label="결과 자동 갱신" inactiveReason="작업 종료로 중지"/>}
    {checkedAt && <p className="media-result-checked">마지막 조회 성공 · <time dateTime={checkedAt.toISOString()}>{checkedAt.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false})}</time></p>}
    <JobIdentifier id={id}/>
    {!directFolder && <RecordFolder key={service+"/"+id} service={service} id={id}/>}
    <MediaResultError error={error} stale={Boolean(job)}/>
    {error && attemptedAt && <p className="media-result-checked">조회 실패 시각 · <time dateTime={attemptedAt.toISOString()}>{attemptedAt.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false})}</time></p>}
    {loading && job && <p role="status">작업 결과를 다시 조회하고 있습니다.</p>}
    {job ? <>
      <p className="media-result-note" role="status">{inGenerator && kind==="audio" && typeof job.note==="string" ? job.note.replace(/^완료 결과와 상세 로그·분리 음원은 해당 생성기 이력에서 확인하세요\.\s*/,"") : job.note}</p>
      {!hideProgress && (["queued","running"].includes(job.status) ? <GenerationProgress job={job} live={live} supportsProgress={kind==="video"} showQueryTime={false} referenceTime={checkedAt}/> : <details><summary>진행 정보 보기</summary><GenerationProgress job={job} supportsProgress={kind==="video"} showQueryTime={false} referenceTime={checkedAt}/></details>)}
      {kind==="audio" && job.result_status==="available" && job.file_observation!=="unavailable" && <div className="media-audio-tracks">
        {(job.tracks?.length ? job.tracks : [{label:"생성 오디오",wav:job.audio}]).map(track=><AudioTrack key={track.wav+":"+mediaRevision} track={track}/>)}
      </div>}
      {kind==="image" && service==="qwen-21-circular" && <CircularComparison key={id+":"+revision} id={id}/>}
      {kind==="character" && job.result_status==="available" && <figure><figcaption>마지막 완료 프레임</figcaption>{renderResultImage("마지막 완료 캐릭터 프레임","media-result-image")}</figure>}
      {["flux","image"].includes(kind) && job.result_status==="available" && <section>
        {renderResultImage(service+" 생성 결과","media-result-image")}
        {service==="flux-seamless" && <SeamlessComparison key={id+":"+revision} id={id}/>}
        <a className="media-result-link" href={job.image} download>결과 PNG 다운로드</a>
      </section>}
      {kind==="video" && job.result_status==="available" && <>
        {service==="dwpose" ? renderResultImage("DWPose 추출 결과","media-result-image") :
          <>
            <video ref={videoRef} key={mediaRevision} aria-label="생성 결과 영상" controls loop playsInline preload="metadata" src={job.video} poster={job.image} style={{maxWidth:"100%"}} onError={()=>setVideoError(true)}/>
            {videoError && <div role="alert"><p>결과 영상을 불러오지 못했습니다. 파일 상태를 확인하세요.</p><button ref={videoRetryRef} type="button" onClick={()=>{const focused=document.activeElement===videoRetryRef.current;setVideoError(false);retryMedia(value=>value+1);if(focused)requestAnimationFrame(()=>{if(document.activeElement===document.body)videoRef.current?.focus();});}}>영상 다시 불러오기</button></div>}
            <a className="media-result-link" href={job.video} target="_blank" rel="noopener noreferrer">MP4 열기</a>
            {directFolder && <RecordFolder key={service+"/"+id} service={service} id={id} direct/>}
          </>}
        {service==="wan22-fun-control" && <SavedPoseVideo key={id} id={id} resultVideo={job.video} resultPoster={job.image}/>}
        {!directFolder && !folderLink && (typeof job.download==="string" && job.download ? <a className="media-result-link" href={job.download} download>{service==="dwpose"?"포즈 PNG·좌표 YAML 다운로드":"PNG 프레임 ZIP 다운로드"}</a> : <p role="status">{service==="dwpose"?"포즈 파일 다운로드 경로":"프레임 ZIP 다운로드 경로"}를 확인할 수 없습니다. 기록 폴더를 확인하세요.</p>)}
      </>}
      {(job.result_status==="unavailable" || job.file_observation==="unavailable") && <p>완료 기록의 결과 파일을 확인할 수 없습니다.</p>}
      {job.result_status==="partial" && job.file_observation!=="unavailable" && <p role="status">완료 기록의 결과 파일 일부만 확인되었습니다. 기록 폴더에서 결과를 확인하세요.</p>}
    </> : !error && <p>결과 조회 중…</p>}
    {children?.(job,()=>refresh(value=>value+1))}
    <div className="media-result-actions">{onReuse && job && <button type="button" onClick={onReuse}>입력 다시 사용</button>}<button ref={refreshRef} type="button" disabled={loading} onClick={()=>{restoreRefreshFocus.current=true;refresh(value=>value+1);}}>{loading?"조회 중…":"결과 새로고침"}</button></div>
  </section>;
}
