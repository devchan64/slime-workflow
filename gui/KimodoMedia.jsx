import React,{useEffect,useRef,useState} from "react";
import ResultTable from "./ResultTable.jsx";
import {imageRetryUrl} from "./imageRetryUrl.mjs";

function KimodoVideo({src}){
  const [error,setError]=useState(false),[revision,retry]=useState(0);
  const videoRef=useRef(null),retryRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>{if(restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)(error ? retryRef : videoRef).current?.focus();}},[error,revision]);
  return error ? <div><p role="alert">선택한 영상을 불러올 수 없습니다. 다시 시도하거나 기록 폴더를 확인하세요.</p><button ref={retryRef} type="button" onClick={()=>{restoreFocus.current=document.activeElement===retryRef.current;setError(false);retry(value=>value+1);}}>영상 다시 불러오기</button></div> :
    <video ref={videoRef} key={revision} aria-label="선택한 결과 영상" controls playsInline preload="metadata" src={imageRetryUrl(src,revision)} onError={event=>{if(event.currentTarget!==videoRef.current)return;restoreFocus.current=document.activeElement===videoRef.current;setError(true);}}/>;
}

export function FaceDepthSummary({summary}){
  if(!summary)return null;
  if(summary.status!=="valid" || !Array.isArray(summary.rows))return <p role="status">얼굴 앵커 깊이 기록 사용 불가 · {summary.message || "기록을 확인할 수 없습니다."}</p>;
  const format=value=>typeof value==="number" && Number.isFinite(value) ? value.toFixed(4) : "미측정";
  return <details><summary>얼굴 앵커 깊이 요약</summary><p>{summary.message}</p><p>단위: {summary.unit}</p>
    <ResultTable table={{title:"얼굴 앵커 깊이",columns:["방향","관절","측정 프레임","중앙값","최솟값","최댓값"],rows:summary.rows.map(row=>[row.direction,row.label,`${row.measured} / ${row.total}`,format(row.median_gap),format(row.min_gap),format(row.max_gap)])}}/>
  </details>;
}

export default function KimodoMedia({id,job}){
  const base="/kimodo/jobs/"+id+"/attempts/"+job.attempt+"/";
  if(!/^[a-f0-9]{32}$/.test(job.attempt) || job.video!==base+"preview.mp4")return <p>원본 영상 경로를 확인할 수 없습니다.</p>;
  return <KimodoMediaForAttempt key={JSON.stringify([id,job.attempt])} id={id} job={job}/>;
}

function KimodoMediaForAttempt({id,job}){
  const [selected,select]=useState(job.video);
  const [selectionNotice,setSelectionNotice]=useState("");
  const base="/kimodo/jobs/"+id+"/attempts/"+job.attempt+"/";
  const videos=[["원본 모션",job.video]];
  if(job.comparison_video===base+"comparison.mp4")videos.push(["포즈 비교",job.comparison_video]);
  const rawVideos=job.preprocess_videos;
  let invalidVideos=rawVideos!=null && (typeof rawVideos!=="object" || Array.isArray(rawVideos));
  const paths=new Set(videos.map(([,path])=>path)),labels=new Set(videos.map(([label])=>label));
  for(const [label,path] of Object.entries(invalidVideos ? {} : rawVideos || {})){
    if(!label.trim() || labels.has(label) || typeof path!=="string" || !path.startsWith(base) || !/^[\w-]+\.mp4$/.test(path.slice(base.length)) || paths.has(path)){invalidVideos=true;continue;}
    labels.add(label);paths.add(path);videos.push([label,path]);
  }
  const currentVideo=videos.some(([,path])=>path===selected) ? selected : job.video;
  useEffect(()=>{if(selected!==currentVideo){select(currentVideo);setSelectionNotice("선택한 영상이 현재 결과에 없어 원본 모션을 표시합니다.");}},[selected,currentVideo]);
  const warnings=Array.isArray(job.quality_warnings) ? job.quality_warnings.filter(value=>typeof value==="string" && value.trim()) : [];
  return <section className="kimodo-media" aria-label="Kimodo 결과 파일">
    {job.direct_pose_status && <p>직접 포즈: {job.direct_pose_status==="completed" ? "생성 완료" : "확인 불가"} · SOMA 관절 투영 결과</p>}
    {job.dwpose_status && <p>DWPose: {job.dwpose_status==="completed" ? "생성 완료" : job.dwpose_status==="warning" ? "생성 오류" : "확인 불가"}{typeof job.dwpose_error==="string" && job.dwpose_error && " · "+job.dwpose_error}</p>}
    <p>원본 모션은 동작 확인용입니다. 포즈 영상은 대상 생성기의 프레임 속도를 확인해 사용하세요.</p>
    {warnings.length>0 && <div><p role="status">포즈 품질 경고 · {warnings.length}건</p><details><summary>경고 상세 보기</summary><ul>{warnings.map((warning,index)=><li key={index}>{warning}</li>)}</ul></details></div>}
    <FaceDepthSummary summary={job.face_anchor_depth_summary}/>
    <label>결과 영상 <select value={currentVideo} onChange={e=>{select(e.target.value);setSelectionNotice("");}}>
      {videos.map(([label,path])=><option key={label} value={path}>{label}</option>)}</select></label>
    {invalidVideos && <p role="status">일부 영상의 이름이나 경로를 확인할 수 없어 목록에서 제외했습니다.</p>}
    {selectionNotice && <p role="status">{selectionNotice}</p>}
    <KimodoVideo key={currentVideo} src={currentVideo}/>
    {job.download===base+"frames.zip" && <a href={job.download} download>프레임 ZIP 다운로드</a>}
  </section>;
}
