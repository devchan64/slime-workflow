import React,{useState} from "react";

export function FaceDepthSummary({summary}){
  if(!summary)return null;
  if(summary.status!=="valid" || !Array.isArray(summary.rows))return <p role="status">얼굴 앵커 깊이 기록 사용 불가 · {summary.message || "기록을 확인할 수 없습니다."}</p>;
  const format=value=>typeof value==="number" && Number.isFinite(value) ? value.toFixed(4) : "미측정";
  return <details><summary>얼굴 앵커 깊이 요약</summary><p>{summary.message}</p><p>단위: {summary.unit}</p>
    <table><thead><tr><th>방향</th><th>관절</th><th>측정 프레임</th><th>중앙값</th><th>최솟값</th><th>최댓값</th></tr></thead><tbody>{summary.rows.map((row,index)=><tr key={index}><td>{row.direction}</td><td>{row.label}</td><td>{row.measured} / {row.total}</td><td>{format(row.median_gap)}</td><td>{format(row.min_gap)}</td><td>{format(row.max_gap)}</td></tr>)}</tbody></table>
  </details>;
}

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
  const warnings=Array.isArray(job.quality_warnings) ? job.quality_warnings.filter(value=>typeof value==="string" && value.trim()) : [];
  return <section className="kimodo-media" aria-label="Kimodo 결과 파일">
    {job.direct_pose_status && <p>직접 포즈: {job.direct_pose_status==="completed" ? "생성 완료" : "확인 불가"} · SOMA 관절 투영 결과</p>}
    {job.dwpose_status && <p>DWPose: {job.dwpose_status==="completed" ? "생성 완료" : job.dwpose_status==="warning" ? "생성 오류" : "확인 불가"}{typeof job.dwpose_error==="string" && job.dwpose_error && " · "+job.dwpose_error}</p>}
    <p>원본 모션은 동작 확인용입니다. 포즈 영상은 대상 생성기의 프레임 속도를 확인해 사용하세요.</p>
    {warnings.length>0 && <div role="status"><p>포즈 품질 경고</p><ul>{warnings.map((warning,index)=><li key={index}>{warning}</li>)}</ul></div>}
    <FaceDepthSummary summary={job.face_anchor_depth_summary}/>
    <label>결과 영상 <select value={selected} onChange={e=>{select(e.target.value);setError("");}}>
      {videos.map(([label,path])=><option key={label} value={path}>{label}</option>)}</select></label>
    <video controls playsInline preload="metadata" src={selected} onError={()=>setError("선택한 영상을 불러올 수 없습니다.")}/>
    {error && <p role="alert">{error}</p>}
    {job.download===base+"frames.zip" && <a href={job.download} download>프레임 ZIP 다운로드</a>}
  </section>;
}
