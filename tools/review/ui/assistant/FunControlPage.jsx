import React,{useEffect,useRef,useState} from "react";
import GeneratorChangelog from "./GeneratorChangelog.jsx";

import GpuQueueSummary from "./GpuQueueSummary.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import {managementCommand} from "./managementCommand.js";

export default function FunControlPage(){
  const [template,setTemplate]=useState(null),[selected,select]=useState("");
  const [request,setRequest]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [pending,setPending]=useState(null),[job,setJob]=useState(new URLSearchParams(location.search).get("job") || "");
  const sending=useRef(false);
  async function submit(){
    if(!pending || sending.current)return;
    sending.current=true;setBusy(true);setError("");
    try{
      const result=await managementCommand("wan22-fun-control","generate",pending);
      if(!result.id)throw new Error("작업 ID를 확인할 수 없습니다.");
      setJob(result.id);
    }catch(problem){setError(problem.message+" · 다시 접수하기 전에 이력을 확인하세요.");}
    finally{sending.current=false;setPending(null);setBusy(false);}
  }
  useEffect(()=>{
    const controller=new AbortController();
    fetch("/management/assistant/fun-template",{signal:controller.signal}).then(async response=>{
      if(!response.ok)throw new Error("예제 목록 조회 실패");
      const data=await response.json();
      if(!controller.signal.aborted){setTemplate(data);select(data.examples[0]?.id || "");}
    }).catch(problem=>{if(!controller.signal.aborted)setError(problem.message);});
    return ()=>controller.abort();
  },[]);
  async function load(){
    setBusy(true);setError("");
    try{
      const response=await fetch("/management/assistant/fun-example/"+encodeURIComponent(selected));
      if(!response.ok)throw new Error("예제 첨부 파일을 불러올 수 없습니다.");
      const example=await response.json();
      if(example.id!==selected)throw new Error("선택한 예제와 응답이 일치하지 않습니다.");
      setRequest(example.request);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <article><h1>Wan Fun Control 영상 생성</h1><GeneratorChangelog generator="wan22-fun-control-generator"/>
    <fieldset disabled={busy || !!pending}><legend>제작 예제</legend>
      <label>예제 선택<select value={selected} onChange={event=>select(event.target.value)}>
        {template?.examples.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <button disabled={!selected} onClick={load}>선택한 예제로 입력 교체</button>
    </fieldset>
    {error && <p role="alert">{error}</p>}
    {request && <fieldset disabled={busy || !!pending}><legend>생성 입력</legend>
      <img alt="외형 참조 이미지" style={{maxWidth:"100%"}} src={"data:image/png;base64,"+request.images[0]}/>
      <video controls loop playsInline preload="metadata" aria-label="입력 포즈 영상" src={"data:video/mp4;base64,"+request.pose_video}/>
      {["prompt","negative_prompt"].map(field=><label key={field}>{field==="prompt"?"동작 프롬프트":"부정 프롬프트"}
        <textarea value={request[field]} onChange={event=>setRequest({...request,[field]:event.target.value})}/></label>)}
      <p>{request.frames}프레임 · 16fps · {request.steps}스텝 · 시드 {request.seed}</p>
      <button disabled={!request.prompt.trim()} onClick={()=>setPending(request)}>대기열에 추가</button>
    </fieldset>}
    {pending && <section aria-label="생성 요청 확인"><GpuQueueSummary/>
      <p>{pending.frames}프레임 · {pending.steps}스텝 · 시드 {pending.seed}</p><p>{pending.prompt}</p>
      <button disabled={busy} onClick={()=>setPending(null)}>취소</button>
      <button disabled={busy} onClick={submit}>확인 후 대기열에 추가</button>
    </section>}
    {job && <MediaJobResult key={job} service="wan22-fun-control" id={job}/>}
  </article>;
}
