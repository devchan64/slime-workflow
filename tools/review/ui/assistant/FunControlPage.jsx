import React,{useEffect,useState} from "react";
import GeneratorChangelog from "./GeneratorChangelog.jsx";

export default function FunControlPage(){
  const [template,setTemplate]=useState(null),[selected,select]=useState("");
  const [request,setRequest]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
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
    <fieldset disabled={busy}><legend>제작 예제</legend>
      <label>예제 선택<select value={selected} onChange={event=>select(event.target.value)}>
        {template?.examples.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <button disabled={!selected} onClick={load}>선택한 예제로 입력 교체</button>
    </fieldset>
    {error && <p role="alert">{error}</p>}
    {request && <fieldset disabled={busy}><legend>생성 입력</legend>
      <img alt="외형 참조 이미지" style={{maxWidth:"100%"}} src={"data:image/png;base64,"+request.images[0]}/>
      <video controls loop playsInline preload="metadata" aria-label="입력 포즈 영상" src={"data:video/mp4;base64,"+request.pose_video}/>
      {["prompt","negative_prompt"].map(field=><label key={field}>{field==="prompt"?"동작 프롬프트":"부정 프롬프트"}
        <textarea value={request[field]} onChange={event=>setRequest({...request,[field]:event.target.value})}/></label>)}
      <p>{request.frames}프레임 · 16fps · {request.steps}스텝 · 시드 {request.seed}</p>
    </fieldset>}
  </article>;
}
