import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ActionButton from "./ActionButton.jsx";
import {videoFrameLimit} from "./videoFrameLimit.mjs";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import SeedInput from "./SeedInput.jsx";
import {referencePng,videoData} from "./videoInputs.js";
import React,{useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import GeneratorHistory from "./GeneratorHistory.jsx";
import DownloadProgress from "./DownloadProgress.jsx";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import ModelReadiness from "./ModelReadiness.jsx";

const service="wan22-vace";
const videoFields={pose:["pose_video"],video_edit:["edit_video","edit_mask"],video_condition:["edit_video"]};
const labels={pose_video:"DWPose MP4",edit_video:"원본 MP4",edit_mask:"마스크 MP4"};
export default function VacePage({embedded=false}={}){
  const [template,setTemplate]=useState(null),[values,setValues]=useState(null),[templateRevision,retryTemplate]=useState(0);
  const [files,setFiles]=useState({}),[model,setModel]=useState(null),[fileErrors,setFileErrors]=useState({});
  const [videoInfo,setVideoInfo]=useState({}),[checking,setChecking]=useState({});
  const videoSequences=useRef({});
  const [busy,setBusy]=useState(false),[pending,setPending]=useState(null);
  const [error,setError]=useState("");
  const [job,setJob]=useState(embedded ? "" : new URLSearchParams(location.search).get("job") || "");
  useEffect(()=>{
    let active=true;
    async function load(){
      try{
        const response=await fetch("/management/assistant/vace-template");
        if(!response.ok)throw new Error("생성 입력 템플릿 조회 실패");
        const spec=await response.json();
        if(active){setTemplate(spec);setValues(old=>old ?? {...spec.defaults,prompt:"",negative_prompt:""});}
        if(active)setError("");
      }catch(problem){if(active)setError(problem.message);}
    }
    load();return ()=>{active=false;};
  },[templateRevision]);
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
    const entries=await Promise.all(Object.entries(restored).filter(([key])=>key!=="reference").map(async ([key,file])=>[key,await inspectVideo(file)]));
    return {...record,files:restored,videoInfo:Object.fromEntries(entries)};
  }
  function restore(request,record){
    for(const key of Object.keys(videoSequences.current))videoSequences.current[key]++;
    setChecking({});setValues({...request});setFiles(record.files);setVideoInfo(record.videoInfo);setFileErrors({});setJob(record.id);setPending(null);
    setNotice(record.id+" 입력을 복원했습니다.");
    refreshHistory(n=>n+1);
  }
  function cleaned(message){setJob("");setNotice(message);refreshHistory(n=>n+1);}
  function field(key,value){setValues(old=>({...old,[key]:value}));}
  async function inspectVideo(file){
    const response=await fetch("/management/assistant/fun-video-info",{method:"POST",body:file});
    const info=await response.json();
    if(!response.ok || !Number.isInteger(info.maximum_frames))throw new Error(info.summary || "영상을 확인할 수 없습니다.");
    return info;
  }
  async function selectVideo(key,file){
    if(!file)return;
    const sequence=(videoSequences.current[key] || 0)+1;videoSequences.current[key]=sequence;
    const problem=file.type!=="video/mp4" ? "MP4 파일을 선택하세요." : file.size>32*1024*1024 ? "MP4당 최대 크기는 32MiB입니다." : "";
    if(problem){setFileErrors(current=>({...current,[key]:problem}));setChecking(current=>({...current,[key]:false}));return;}
    setFileErrors(current=>({...current,[key]:""}));setChecking(current=>({...current,[key]:true}));
    try{
      const info=await inspectVideo(file);
      if(videoSequences.current[key]===sequence){setFiles(current=>({...current,[key]:file}));setVideoInfo(current=>({...current,[key]:info}));}
    }catch(error){if(videoSequences.current[key]===sequence)setFileErrors(current=>({...current,[key]:error.message}));}
    finally{if(videoSequences.current[key]===sequence)setChecking(current=>({...current,[key]:false}));}
  }
  const attachments=videoFields[values?.mode] || [];
  const checkingVideo=attachments.some(key=>checking[key]);
  const missingVideoInfo=attachments.some(key=>files[key] && !videoInfo[key]);
  const frameLimit=videoFrameLimit(attachments,videoInfo);
  const invalidFrames=frameLimit!==null && Number(values.frames)>frameLimit;
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
  const session=new URLSearchParams(location.search).get("session");
  return <article className="vace-page"><a href={"/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화로 돌아가기</a><h1>Wan VACE 영상 생성</h1><GeneratorChangelog generator="wan22-vace-generator"/>
    <ModelReadiness service={service} onStatus={setModel}/>
    <DownloadProgress service={service}/>
    {error && <p role="alert">{error}</p>}
    {!template && error && <button type="button" onClick={()=>retryTemplate(value=>value+1)}>생성 입력 다시 불러오기</button>}
    {values && <form onSubmit={review}><fieldset disabled={busy || !!pending}><legend>생성 입력</legend>
      <label>생성 모드<select value={values.mode} onChange={e=>field("mode",e.target.value)}>{template.modes.map(m=><option key={m.id} value={m.id}>{m.label}</option>)}</select></label>
      <p style={{whiteSpace:"pre-line"}}>{template.modes.find(m=>m.id===values.mode)?.help.replaceAll("**","")}</p>
      {Object.entries({reference:"참조 또는 첫 프레임 이미지",...labels}).map(([key,label])=>{
        const visible=key==="reference"?values.mode!=="text":attachments.includes(key);
        return <div key={key} hidden={!visible}>{key==="reference" ? <ReferenceImageInput disabled={busy || !!pending || !visible} label={label} source={files[key]} onChange={file=>setFiles({...files,[key]:file})}/> : <div><label>{label}<input key={historyRevision} type="file" accept="video/mp4" required={visible && !files[key]} disabled={!visible}
          onChange={e=>{selectVideo(key,e.target.files[0]);e.target.value="";}}/></label><p>MP4 · 파일당 최대 32MiB{files[key] && " · 선택: "+files[key].name}</p>
          {checking[key] && <p role="status">영상 정보 확인 중…</p>}
          {videoInfo[key] && <p>{videoInfo[key].summary}</p>}
          {fileErrors[key] && <p role="alert">{fileErrors[key]}{files[key] && " 기존 영상은 유지됩니다."}</p>}</div>}</div>;
      })}
      {["prompt","negative_prompt"].map(key=>{
        return <label key={key}>{key==="prompt"?"장면·동작 프롬프트":"부정 프롬프트"}<textarea maxLength={8000} required={key==="prompt"} value={values[key]} onChange={e=>field(key,e.target.value)}/><PromptWordCount text={values[key]} final/></label>;
      })}
      {[["frames","출력 프레임",5,129,4],["steps","스텝",2,100,1],["flow_shift","Flow shift",0.1,20,"any"],["guidance_scale","CFG",1,10,"any"],["reference_strength","조건 강도",0.1,2,"any"]].map(([key,label,min,max,step])=>
        <label key={key}>{label}<input type="number" required min={min} max={max} step={step} value={values[key]} onChange={e=>field(key,e.target.value===""?"":Number(e.target.value))}/></label>)}
      {frameLimit!==null && <p>입력에 사용할 수 있는 최대 출력 길이 {frameLimit}프레임 <button type="button" onClick={()=>field("frames",frameLimit)}>최대 프레임 적용</button></p>}
      {invalidFrames && <p role="alert">출력 프레임이 입력 영상보다 깁니다. {frameLimit}프레임 이하로 줄이세요.</p>}
      <p>832×480 · 16fps · {Number(values.frames)>0?(Number(values.frames)/16).toFixed(2):"0"}초 · VACE-Fun A14B BF16 · Euler/FlowMatch</p>
      <SeedInput value={values.seed} max={template.maximum_seed} onChange={value=>field("seed",value===""?"":Number(value))}/>
      <ActionButton type="submit" reasons={[
        !model?.ready && "모델 준비 상태를 확인하세요.",
        !values.prompt.trim() && "프롬프트를 입력하세요.",
        values.mode!=="text" && !files.reference && "참조 이미지를 선택하세요.",
        attachments.some(key=>!files[key]) && "필수 영상을 선택하세요.",
        checkingVideo && "영상 정보를 확인하고 있습니다.",
        missingVideoInfo && "영상 정보를 확인하세요.",
        invalidFrames && "출력 프레임 수를 입력 영상에 맞게 조정하세요."
      ]}>생성 요청 검토</ActionButton>
    </fieldset></form>}
    {pending && <section><GpuQueueSummary/><p>{template.modes.find(mode=>mode.id===pending.mode)?.label || pending.mode} · {pending.frames}프레임 · 16fps · {(pending.frames/16).toFixed(2)}초 · 시드 {pending.seed}</p><p>{pending.prompt}</p>{attachments.map(key=><p key={key}>{labels[key]} · {videoInfo[key]?.summary || "영상 정보 확인 불가"}</p>)}{pending.mode==="video_edit" && <p>마스크의 편집·보존 영역은 접수 시 추가 검증합니다.</p>}
      <GenerationReviewActions busy={busy} onCancel={()=>setPending(null)} onConfirm={submit}/></section>}
    <fieldset disabled={busy || !!pending}><GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id) cleaned(message); else setNotice(message);}} key={historyRevision} service={service} readJob={readJob} openResult={setJob} restore={restore}/></fieldset>
    {notice && <p role="status">{notice}</p>}
    {job ? <MediaJobResult key={job} service={service} id={job}>
      {(record,reload)=>record && <React.Fragment key={record.status}>
        <GeneratorJobControls showActions={false} service={service} id={job} state={record.status} refresh={reload}/>
        <HistoryCleanup allowSelected={false} service={service} job={job} state={record.status} onDeleted={cleaned}/>
      </React.Fragment>}
    </MediaJobResult> : <HistoryCleanup allowSelected={false} service={service} onDeleted={cleaned}/>}
  </article>;
}
