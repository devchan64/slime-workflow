import HistoryCleanup from "./HistoryCleanup.jsx";
import KimodoMedia from "./KimodoMedia.jsx";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import KimodoKeyframeSave from "./KimodoKeyframeSave.jsx";
import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";

export default function KimodoFrames({id,choose,onDeleted}) {
  const [source,setSource]=useState(null);
  const [revision,refresh]=useState(0);
  const [frame,setFrame]=useState("1");
  const [preview,setPreview]=useState(null);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  useEffect(()=>{
    let active=true;setPreview(null);setSource(null);setError("");
    managementCommand("kimodo","status",{id}).then(job=>{
      if(!job.status || (job.status==="completed" && (job.image!=="/kimodo/jobs/"+id+"/attempts/"+job.attempt+"/output-000.png" || !job.attempt || !Number.isInteger(job.source_frame_count) || job.source_frame_count<1)))
        throw new Error("완료된 모션의 원본 프레임을 확인할 수 없습니다.");
      if(active)setSource(job);
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[id,revision]);
  async function inspect(event){
    event.preventDefault();setBusy(true);setError("");setPreview(null);
    try{
      const request={job_id:id,attempt_id:source.attempt,frame:Number(frame)};
      const result=await managementCommand("hermes-agent","hermes-kimodo-source-frame",request);
      const path="/kimodo/jobs/"+id+"/attempts/"+source.attempt+"/output-"+String(request.frame-1).padStart(3,"0")+".png";
      if(result.image!==path || result.frame!==request.frame || result.attempt_id!==source.attempt || result.job_id!==id)
        throw new Error("선택한 원본 프레임과 조회 결과가 일치하지 않습니다.");
      setPreview(result);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <section aria-label="Kimodo 원본 프레임">
    {error && <p role="alert">{error}</p>}
    {source && <><p>{id} · {source.status} {source.error}</p>
      <button onClick={()=>refresh(value=>value+1)}>작업 상태 갱신</button>
      <GeneratorJobControls service="kimodo" id={id} state={source.status} refresh={()=>refresh(value=>value+1)}/></>}
    <HistoryCleanup key={id+"/"+(source?.status || "")} service="kimodo" job={id} state={source?.status} onDeleted={onDeleted}/>
    {source?.status==="completed" && <KimodoMedia key={source.attempt} id={id} job={source}/>}
    {source?.status==="completed" && <form onSubmit={inspect}><fieldset disabled={busy}><legend>원본 SOMA 관절 · {source.source_frame_count}프레임</legend>
      <label>원본 프레임 번호 <input type="number" min="1" max={source.source_frame_count} required value={frame}
        onChange={event=>{setFrame(event.target.value);setPreview(null);setError("");}}/></label>
      <button>프레임 조회</button>
    </fieldset></form>}
    {preview && <figure><img src={preview.image} alt={id+" 원본 "+preview.frame+"프레임"} style={{maxWidth:"100%"}}/>
      <figcaption>{preview.frame} / {preview.frame_count} · {preview.fps} fps</figcaption>
      <button type="button" onClick={()=>choose("Kimodo 원본 프레임",JSON.stringify({job_id:id,attempt_id:source.attempt,frame:preview.frame}))}>이 프레임을 대화 입력에 추가</button>
      <KimodoKeyframeSave preview={preview} choose={choose}/>
    </figure>}
  </section>;
}
