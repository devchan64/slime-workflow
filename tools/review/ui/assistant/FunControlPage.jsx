import React,{useEffect,useRef,useState} from "react";
import {referencePng,videoData} from "./videoInputs.js";
import GeneratorChangelog from "./GeneratorChangelog.jsx";

import GpuQueueSummary from "./GpuQueueSummary.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import {managementCommand} from "./managementCommand.js";

export default function FunControlPage(){
  const [template,setTemplate]=useState(null),[selected,select]=useState("");
  const [request,setRequest]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [pending,setPending]=useState(null),[job,setJob]=useState(new URLSearchParams(location.search).get("job") || "");
  const [videoInfo,setVideoInfo]=useState(null);
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
      if(!controller.signal.aborted){setTemplate(data);setRequest({...data.defaults,action:"generate",control_type:"pose",width:832,height:480,images:[],pose_video:"",prompt:"",negative_prompt:""});select(data.examples[0]?.id || "");}
    }).catch(problem=>{if(!controller.signal.aborted)setError(problem.message);});
    return ()=>controller.abort();
  },[]);
  async function attach(file,field){
    if(!file)return;
    setBusy(true);setError("");
    try{
      const value=field==="images"?[await referencePng(file)]:await videoData(file);
      if(field==="pose_video"){
        const response=await fetch("/management/assistant/fun-video-info",{method:"POST",body:file});
        const info=await response.json();
        if(!response.ok)throw new Error(info.summary || "포즈 영상을 확인할 수 없습니다.");
        setVideoInfo(info);
      }
      setRequest(current=>({...current,[field]:value}));
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  async function load(restore=false){
    setBusy(true);setError("");
    try{
      const id=restore?job:selected;
      const response=await fetch("/management/assistant/"+(restore?"fun-input/":"fun-example/")+encodeURIComponent(id));
      if(!response.ok)throw new Error(restore?"이 작업의 입력 사본을 복원할 수 없습니다.":"예제 첨부 파일을 불러올 수 없습니다.");
      const example=await response.json();
      if(example.id!==id)throw new Error("선택한 예제와 응답이 일치하지 않습니다.");
      setVideoInfo(example.video);
      setRequest(example.request);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  const frameLimit=videoInfo?.maximum_frames ?? template?.maximum_frames;
  const settings=[
    ["frames","프레임 수",5,frameLimit,4],
    ["steps","스텝",2,100,1],
    ["seed","시드",0,template?.maximum_seed,1],
    ["flow_shift","Flow shift",0.1,20,"any"],
    ["guidance_scale","Guidance scale",1,10,"any"],
    ["switch_ratio","모델 전환 비율",0.1,0.9,"any"],
  ];
  function review(event){
    event.preventDefault();
    const values=Object.fromEntries(settings.map(([key])=>[key,Number(request[key])]));
    setPending({...request,...values});
  }
  return <article><h1>Wan Fun Control 영상 생성</h1><GeneratorChangelog generator="wan22-fun-control-generator"/>
    <fieldset disabled={busy || !!pending}><legend>제작 예제</legend>
      <label>예제 선택<select value={selected} onChange={event=>select(event.target.value)}>
        {template?.examples.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <button disabled={!selected} onClick={()=>load()}>선택한 예제로 입력 교체</button>
      {job && <button disabled={!template} onClick={()=>load(true)}>작업 {job} 입력으로 교체</button>}
    </fieldset>
    {error && <p role="alert">{error}</p>}
    {request && <form onSubmit={review}><fieldset disabled={busy || !!pending}><legend>생성 입력</legend>
      <label>외형 참조 이미지<input type="file" accept="image/*" onChange={event=>attach(event.target.files[0],"images")}/></label>
      <label>처리된 포즈 MP4 · 832×480 · 16fps<input type="file" accept="video/mp4" onChange={event=>attach(event.target.files[0],"pose_video")}/></label>
      {request.images[0] && <img alt="외형 참조 이미지" style={{maxWidth:"100%"}} src={"data:image/png;base64,"+request.images[0]}/>}
      {request.pose_video && <video controls loop playsInline preload="metadata" aria-label="입력 포즈 영상" src={"data:video/mp4;base64,"+request.pose_video}/>}
      {videoInfo && <div><p>{videoInfo.summary}</p><button type="button"
        onClick={()=>setRequest({...request,frames:frameLimit})}>입력 영상의 최대 프레임 적용</button></div>}
      {["prompt","negative_prompt"].map(field=><label key={field}>{field==="prompt"?"동작 프롬프트":"부정 프롬프트"}
        <textarea maxLength={8000} value={request[field]} onChange={event=>setRequest({...request,[field]:event.target.value})}/></label>)}
      <label>모델<select value={request.model_profile || "wan22-14b"} onChange={event=>setRequest({...request,model_profile:event.target.value})}>
        {template.models?.map(model=><option key={model.id} value={model.id}>{model.label}</option>)}</select></label>
      <fieldset><legend>출력 프레임 빠른 선택</legend>
        {[21,41,81,129].filter(count=>count<=frameLimit).map(count=>
          <button key={count} type="button" aria-pressed={Number(request.frames)===count}
            onClick={()=>setRequest({...request,frames:count})}>{count}프레임</button>)}
      </fieldset>
      {settings.map(([key,label,min,max,step])=><label key={key}>{label}
        <input required type="number" min={min} max={max} step={step} value={request[key]}
          onChange={event=>setRequest({...request,[key]:event.target.value})}/></label>)}
      {Number(request.frames)>=5 && Number(request.frames)<=template.maximum_frames && Number(request.frames)%4===1 &&
        <p>출력 길이 {(Number(request.frames)/16).toFixed(2)}초 · 16fps</p>}
      <button disabled={!request.prompt.trim() || !request.images[0] || !request.pose_video} type="submit">대기열에 추가</button>
    </fieldset></form>}
    {pending && <section aria-label="생성 요청 확인"><GpuQueueSummary/>
      <p>{pending.frames}프레임 · {pending.steps}스텝 · 시드 {pending.seed}</p><p>{pending.prompt}</p>
      <button disabled={busy} onClick={()=>setPending(null)}>취소</button>
      <button disabled={busy} onClick={submit}>확인 후 대기열에 추가</button>
    </section>}
    {job && <MediaJobResult key={job} service="wan22-fun-control" id={job}/>}
  </article>;
}
