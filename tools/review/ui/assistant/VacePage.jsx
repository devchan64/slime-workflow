import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import GeneratorHistory from "./GeneratorHistory.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";

const service="wan22-vace";
const videoFields={pose:["pose_video"],video_edit:["edit_video","edit_mask"],video_condition:["edit_video"]};
const labels={pose_video:"DWPose MP4",edit_video:"원본 MP4",edit_mask:"마스크 MP4"};
async function referencePng(file){
  const image=await createImageBitmap(file);
  try{
    const canvas=document.createElement("canvas");
    canvas.width=832;canvas.height=480;
    const ctx=canvas.getContext("2d");
    ctx.fillStyle="white";ctx.fillRect(0,0,832,480);
    const scale=Math.min(832/image.width,480/image.height);
    const w=Math.round(image.width*scale),h=Math.round(image.height*scale);
    ctx.drawImage(image,Math.floor((832-w)/2),Math.floor((480-h)/2),w,h);
    return canvas.toDataURL("image/png").split(",")[1];
  }finally{image.close();}
}
function videoData(file){
  if(file.size>32*1024*1024)throw new Error("MP4당 최대 크기는 32MiB입니다.");
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(reader.result.split(",")[1]);
    reader.onerror=()=>reject(new Error("영상을 읽을 수 없습니다."));
    reader.readAsDataURL(file);
  });
}
export default function VacePage(){
  const [template,setTemplate]=useState(null),[values,setValues]=useState(null);
  const [files,setFiles]=useState({}),[model,setModel]=useState(null);
  const [busy,setBusy]=useState(false),[pending,setPending]=useState(null);
  const [error,setError]=useState(""),[revision,refresh]=useState(0);
  const [job,setJob]=useState(new URLSearchParams(location.search).get("job") || "");
  useEffect(()=>{
    let active=true;
    async function load(){
      try{
        const response=await fetch("/management/assistant/vace-template");
        if(!response.ok)throw new Error("생성 입력 템플릿 조회 실패");
        const spec=await response.json();
        if(active){setTemplate(spec);setValues(old=>old ?? {...spec.defaults,prompt:"",negative_prompt:""});}
        const state=await managementCommand(service,"model-status",{});
        if(active){setModel(state);setError("");}
      }catch(problem){if(active)setError(problem.message);}
    }
    load();return ()=>{active=false;};
  },[revision]);
  const [historyRevision,refreshHistory]=useState(0);
  const [notice,setNotice]=useState("");
  async function readJob(id){
    const prefix="/management/assistant/vace-input/"+encodeURIComponent(id)+"/";
    const response=await fetch(prefix+"request",{cache:"no-store"});
    if(!response.ok)throw new Error("저장된 입력 사본을 확인할 수 없습니다.");
    const record=await response.json();
    const restored={};
    for(const key of record.attachments){
      const attachment=await fetch(prefix+key,{cache:"no-store"});
      if(!attachment.ok)throw new Error("첨부 사본을 읽을 수 없습니다.");
      const blob=await attachment.blob();
      restored[key]=new File([blob],key+(key==="reference"?".png":".mp4"),{type:blob.type});
    }
    return {...record,files:restored};
  }
  function restore(request,record){
    setValues({...request});setFiles(record.files);setJob(record.id);setPending(null);
    setNotice(record.id+" 입력을 복원했습니다.");
    refreshHistory(n=>n+1);
  }
  function cleaned(message){setJob("");setNotice(message);refreshHistory(n=>n+1);}
  function field(key,value){setValues(old=>({...old,[key]:value}));}
  const attachments=videoFields[values?.mode] || [];
  async function review(event){
    event.preventDefault();setBusy(true);setError("");
    try{
      const request={...values,action:"generate",width:832,height:480,images:[]};
      if(values.mode!=="text")request.images.push(await referencePng(files.reference));
      for(const key of attachments)request[key]=await videoData(files[key]);
      setPending(request);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  async function submit(){
    setBusy(true);setError("");setPending(null);
    try{
      const result=await managementCommand(service,"generate",pending);
      if(!result.id)throw new Error("접수 ID를 확인할 수 없습니다.");
      setJob(result.id);
    }catch(problem){setError(problem.message+" · 재접수 전에 생성 이력을 확인하세요.");}
    finally{setBusy(false);}
  }
  return <article><h1>Wan VACE 영상 생성</h1><GeneratorChangelog generator="wan22-vace-generator"/>
    <button disabled={busy || !!pending} onClick={()=>{setModel(null);refresh(v=>v+1);}}>모델 상태 확인</button>
    <p role="status">{model?.message || "모델 상태 확인 중"}</p>
    {error && <p role="alert">{error}</p>}
    {values && <form onSubmit={review}><fieldset disabled={busy || !!pending}><legend>생성 입력</legend>
      <label>생성 모드<select value={values.mode} onChange={e=>field("mode",e.target.value)}>{template.modes.map(m=><option key={m.id} value={m.id}>{m.label}</option>)}</select></label>
      <p style={{whiteSpace:"pre-line"}}>{template.modes.find(m=>m.id===values.mode)?.help.replaceAll("**","")}</p>
      {Object.entries({reference:"참조 또는 첫 프레임 이미지",...labels}).map(([key,label])=>{
        const visible=key==="reference"?values.mode!=="text":attachments.includes(key);
        return <div key={key} hidden={!visible}><label>{label}<input key={historyRevision} type="file" accept={key==="reference"?"image/*":"video/mp4"} required={visible && !files[key]} disabled={!visible}
          onChange={e=>setFiles({...files,[key]:e.target.files[0]})}/>{files[key]?.name}</label></div>;
      })}
      {["prompt","negative_prompt"].map(key=>{
        const words=values[key].trim().split(/\s+/).filter(Boolean).length;
        return <label key={key}>{key==="prompt"?"장면·동작 프롬프트":"부정 프롬프트"}<textarea maxLength={8000} required={key==="prompt"} value={values[key]} onChange={e=>field(key,e.target.value)}/>원문 {words}단어 · 최종 {words}단어</label>;
      })}
      {[["frames","출력 프레임",5,129,4],["steps","스텝",2,100,1],["seed","시드",0,template.maximum_seed,1],["flow_shift","Flow shift",0.1,20,"any"],["guidance_scale","CFG",1,10,"any"],["reference_strength","조건 강도",0.1,2,"any"]].map(([key,label,min,max,step])=>
        <label key={key}>{label}<input type="number" required min={min} max={max} step={step} value={values[key]} onChange={e=>field(key,e.target.value===""?"":Number(e.target.value))}/></label>)}
      <button type="button" onClick={()=>field("seed",crypto.getRandomValues(new Uint32Array(1))[0] >>> 1)}>랜덤 시드</button>
      <button disabled={!model?.ready || !values.prompt.trim()}>대기열에 추가</button>
    </fieldset></form>}
    {pending && <section><GpuQueueSummary/><p>{pending.mode} · {pending.frames}프레임 · 시드 {pending.seed}</p>
      <button onClick={()=>setPending(null)}>취소</button><button onClick={submit}>확인 후 대기열에 추가</button></section>}
    <fieldset disabled={busy || !!pending}><GeneratorHistory key={historyRevision} service={service} readJob={readJob} openResult={setJob} restore={restore}/></fieldset>
    {notice && <p role="status">{notice}</p>}
    {job ? <MediaJobResult key={job} service={service} id={job}>
      {record=><HistoryCleanup key={record?.status} service={service} job={job} state={record?.status} onDeleted={cleaned}/>}
    </MediaJobResult> : <HistoryCleanup service={service} onDeleted={cleaned}/>}
  </article>;
}
