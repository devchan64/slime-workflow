import React,{useState} from "react";

export default function KimodoMedia({id,job}){
  const [selected,select]=useState(job.video);
  const [error,setError]=useState("");
  const base="/kimodo/jobs/"+id+"/attempts/"+job.attempt+"/";
  if(!/^[a-f0-9]{32}$/.test(job.attempt) || job.video!==base+"preview.mp4")return <p>원본 영상 경로를 확인할 수 없습니다.</p>;
  const videos=[["원본 모션",job.video]];
  if(job.comparison_video===base+"comparison.mp4")videos.push(["포즈 비교",job.comparison_video]);
  for(const [label,path] of Object.entries(job.preprocess_videos || {})){
    if(typeof path==="string" && path.startsWith(base) && /^[\w-]+\.mp4$/.test(path.slice(base.length)))videos.push([label,path]);
  }
  return <section className="kimodo-media" aria-label="Kimodo 결과 파일">
    <label>결과 영상 <select value={selected} onChange={e=>{select(e.target.value);setError("");}}>
      {videos.map(([label,path])=><option key={label} value={path}>{label}</option>)}</select></label>
    <video controls playsInline preload="metadata" src={selected} onError={()=>setError("선택한 영상을 불러올 수 없습니다.")}/>
    {error && <p role="alert">{error}</p>}
    {job.download===base+"frames.zip" && <a href={job.download} download>프레임 ZIP 다운로드</a>}
  </section>;
}
