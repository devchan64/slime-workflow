import {generationReady} from "./generationReady.mjs";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import useGpuHandoff from "./useGpuHandoff.js";
import ActionButton from "./ActionButton.jsx";
import {videoFrameLimit} from "./videoFrameLimit.mjs";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import InputVideoPreview from "./InputVideoPreview.jsx";
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
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorSectionNavigation from "./GeneratorSectionNavigation.jsx";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import {requestErrorMessage} from "./requestError.mjs";
import {generationProposalScope,readGenerationProposal,vaceProposalInputs} from "./generationProposal.mjs";

const service="wan22-vace";
const videoFields={pose:["pose_video"],video_edit:["edit_video","edit_mask"],video_condition:["edit_video"]};
const labels={pose_video:"DWPose MP4",edit_video:"원본 MP4",edit_mask:"마스크 MP4"};
function SavedVaceInputs({id}){
  const [state,setState]=useState({id,loading:true}),[revision,retry]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();setState({id,loading:true});
    (async()=>{try{
      const response=await fetch('/management/assistant/vace-input/'+encodeURIComponent(id)+'/request',{cache:'no-store',signal:controller.signal});
      if(!response.ok)throw new Error('저장 입력을 불러오지 못했습니다.');
      const data=await response.json();if(data.id!==id || !data.request || !Array.isArray(data.attachments))throw new Error('저장 입력이 선택한 작업과 일치하지 않습니다.');
      if(!controller.signal.aborted)setState({id,data});
    }catch(error){if(!controller.signal.aborted)setState({id,error:error.message});}})();
    return ()=>controller.abort();
  },[id,revision]);
  if(state.id!==id || state.loading)return <p role="status">저장 입력을 불러오는 중입니다.</p>;
  if(state.error)return <div role="alert">{state.error} <button type="button" onClick={()=>retry(value=>value+1)}>입력 정보 다시 조회</button></div>;
  const {request,attachments}=state.data;
  return <section className="history-action-detail" aria-label="저장된 생성 입력"><strong>저장된 생성 입력</strong><p>{request.frames}프레임 · {request.steps}스텝 · 시드 {request.seed} · 첨부 {attachments.length ? attachments.map(key=>labels[key] || (key==='reference'?'참조 이미지':key)).join(', ') : '없음'}</p><details><summary>저장된 입력 상세</summary><pre>{JSON.stringify(request,null,2)}</pre></details></section>;
}
export default function VacePage({embedded=false,session:embeddedSession=""}={}){
  const session=embeddedSession || new URLSearchParams(location.search).get("session") || "";
  const [template,setTemplate]=useState(null),[values,setValues]=useState(null),[templateRevision,retryTemplate]=useState(0);
  const [files,setFiles]=useState({}),[model,setModel]=useState(null),[fileErrors,setFileErrors]=useState({});
  const [videoInfo,setVideoInfo]=useState({}),[checking,setChecking]=useState({});
  const videoSequences=useRef({}),formRef=useRef(null),reviewRef=useRef(null),resultRef=useRef(null),historyRef=useRef(null),sending=useRef(false),focusResult=useRef(false);
  const [busy,setBusy]=useState(false),[pending,setPending]=useState(null),[modelError,setModelError]=useState("");
  useEffect(()=>{if(pending)reviewRef.current?.focus();},[pending]);
  const [error,setError]=useState("");
  const [templateError,setTemplateError]=useState("");
  const [job,setJob]=useState(embedded ? "" : new URLSearchParams(location.search).get("job") || "");
  const [sourceJob,setSourceJob]=useState("");
  useEffect(()=>{
    let active=true;
    async function load(){
      setTemplateError("");
      try{
        const response=await fetch("/management/assistant/vace-template");
        if(!response.ok)throw new Error("생성 입력 템플릿 조회 실패");
        const spec=await response.json();
        let initial={...spec.defaults,prompt:"",negative_prompt:""};
        if(!embedded){
          try{
            const scope=generationProposalScope(location.search,session,'video');
            if(scope){initial=vaceProposalInputs(initial,await readGenerationProposal(managementCommand,scope));if(active)setNotice('대화 제안 입력을 불러왔습니다. 필요한 첨부와 설정을 확인하세요.');}
          }catch(problem){if(active)setError('대화 제안을 불러오지 못했습니다 · '+problem.message);}
        }
        if(active){setTemplate(spec);setValues(old=>old ?? initial);}
      }catch(problem){if(active)setTemplateError(requestErrorMessage(problem));}
    }
    load();return ()=>{active=false;};
  },[templateRevision]);
  useEffect(()=>{if(template && templateRevision>0 && document.activeElement===document.body)formRef.current?.focus();},[template,templateRevision]);
  const [historyRevision,refreshHistory]=useState(0);
  const [notice,setNotice]=useState("");
  const handoff=useGpuHandoff(session,service,setJob,setError);
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
    setChecking({});setValues({...request});setFiles(record.files);setVideoInfo(record.videoInfo);setFileErrors({});setJob(record.id);setSourceJob(record.id);setPending(null);
    setNotice(record.id+" 입력을 복원했습니다.");
    requestAnimationFrame(()=>{const form=formRef.current;const card=form?.closest('details');if(card)card.open=true;form?.focus();form?.scrollIntoView({block:'start'});});
  }
  function cleaned(message){setJob("");setNotice(message);refreshHistory(n=>n+1);}
  function openResult(id){focusResult.current=true;if(id===job){const card=historyRef.current?.querySelector('details.generator-history');if(card)card.open=true;resultRef.current?.focus();focusResult.current=false;}else setJob(id);}
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
      await handoff.preview(request);setPending(request);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  async function submit(){
    if(!pending || sending.current || !generationReady(model))return;
    sending.current=true;
    setBusy(true);setError("");setPending(null);
    try{
      if(handoff.review){await handoff.approve(pending);setNotice("확인한 GPU 양도 요청을 접수했습니다.");return;}
      const result=await managementCommand(service,"generate",pending);
      if(!result.id)throw new Error("접수 ID를 확인할 수 없습니다.");
      setJob(result.id);
    }catch(problem){setError(problem.message+" · 재접수 전에 생성 이력을 확인하세요.");}
    finally{handoff.clearReview();sending.current=false;setBusy(false);}
  }
  return <article className={"vace-page generator-page-common"+(embedded ? "" : " vace-standalone")}><GeneratorPageIdentity service={service} embedded={embedded} session={session} showReturn changelogCard/>
    <GeneratorSectionCard title="사용 설명" summary="생성 방식과 입력 안내" className="vace-usage-card">
      <p>참조 이미지, 첫 프레임 또는 제어 영상을 프롬프트와 함께 사용해 영상을 생성합니다. 프롬프트만으로도 생성할 수 있습니다.</p>
      <ol><li>모델 준비 상태를 확인합니다.</li><li>생성 입력에서 원하는 생성 모드를 선택하고 화면에 표시되는 필수 자료를 첨부합니다.</li><li>장면·동작과 카메라를 입력하고 출력 길이와 설정을 확인합니다.</li><li>생성 요청을 검토해 접수한 후 현재 생성 작업과 이력에서 진행 상황과 결과를 확인합니다.</li></ol>
      <p>포즈 제어는 DWPose MP4를 사용합니다. 영상 입력은 832×480·16fps, 파일당 32MiB 이하이며 출력 길이는 입력 영상 이내여야 합니다. 모드별 상세 안내와 입력 오류는 생성 입력에 표시됩니다.</p>
      <p>참조 이미지는 외형 조건이며 동작이나 첫 화면의 일치를 보장하지 않습니다. 첫 프레임 조건도 픽셀의 완전 일치를 보장하지 않습니다. 영상 편집의 흰색 마스크는 재생성, 검정색은 보존 조건이며 마스크 밖도 달라질 수 있습니다.</p>
    </GeneratorSectionCard><GeneratorSectionNavigation inputRef={formRef} historyRef={historyRef} resultRef={resultRef} inputReady={Boolean(values)} resultReady={Boolean(job)} openOnNavigate/>
    <GeneratorSectionCard title="모델 준비" summary={modelError ? "모델 상태 조회 실패" : !model ? "상태 확인 필요" : (model.generation_ready ?? model.ready) ? "준비 완료" : "준비 필요"} defaultOpen>
      <ModelReadiness service={service} onStatus={setModel} onError={setModelError}/>
      {embedded && (model?.generation_ready ?? model?.ready) && !["queued","running","failed","cancelled","unknown"].includes(model?.preparation_status) ? <details><summary>모델 다운로드 이력</summary><DownloadProgress service={service}/></details> : <DownloadProgress service={service}/>}
    </GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={historyRevision+":"+job} onOpenResult={openResult}/>
    {error && <p role="alert">{error}</p>}
    {templateError && <p role="alert">{templateError}</p>}
    {!template && !templateError && <p role="status">생성 입력을 불러오는 중입니다.</p>}
    {!template && templateError && <button type="button" onClick={()=>retryTemplate(value=>value+1)}>생성 입력 다시 불러오기</button>}
    {handoff.id && <GpuHandoffStatus session={session} id={handoff.id} service={service} status={handoff.status} onUpdate={handoff.update} onClose={handoff.close}/>}
    {values && <GeneratorSectionCard title="생성 입력" summary={template.modes.find(mode=>mode.id===values.mode)?.label || "설정 확인"} defaultOpen className="vace-input-card"><form ref={formRef} tabIndex={-1} aria-label="생성 입력" onSubmit={review}><fieldset disabled={busy || !!pending || Boolean(handoff.id)}><legend className="generator-visually-hidden">생성 입력</legend>
      {sourceJob && <div><p>불러온 원본 작업</p><JobIdentifier id={sourceJob} compact/></div>}
      <div className="vace-input-group"><h2>입력 자료</h2><p className="vace-group-help">생성 방식과 필요한 참조 자료를 선택하세요.</p>
      <label>생성 모드<select value={values.mode} onChange={e=>field("mode",e.target.value)}>{template.modes.map(m=><option key={m.id} value={m.id}>{m.label}</option>)}</select></label>
      {embedded ? <details><summary>선택한 생성 모드 안내</summary><p style={{whiteSpace:"pre-line"}}>{template.modes.find(m=>m.id===values.mode)?.help.replaceAll("**","")}</p></details> : <p style={{whiteSpace:"pre-line"}}>{template.modes.find(m=>m.id===values.mode)?.help.replaceAll("**","")}</p>}
      {Object.entries({reference:"참조 또는 첫 프레임 이미지",...labels}).map(([key,label])=>{
        const visible=key==="reference"?values.mode!=="text":attachments.includes(key);
        return <div key={key} hidden={!visible}>{key==="reference" ? <ReferenceImageInput disabled={busy || !!pending || !visible} label={label} source={files[key]} onChange={file=>setFiles({...files,[key]:file})}/> : <div><label>{label}<input key={historyRevision} type="file" accept="video/mp4" required={visible && !files[key]} disabled={!visible}
          onChange={e=>{selectVideo(key,e.target.files[0]);e.target.value="";}}/></label><p>MP4 · 파일당 최대 32MiB{files[key] && " · 선택: "+files[key].name}</p>
          {checking[key] && <p role="status">영상 정보 확인 중…</p>}
          {videoInfo[key] && <p>{videoInfo[key].summary}</p>}
          {fileErrors[key] && <p role="alert">{fileErrors[key]}{files[key] && " 기존 영상은 유지됩니다."}</p>}
          {visible && <InputVideoPreview file={files[key]} label={label}/>}</div>}</div>;
      })}
      </div><div className="vace-input-group"><h2>장면 지시</h2><p className="vace-group-help">인물·동작·카메라를 설명하세요.</p>
      {["prompt","negative_prompt"].map(key=>{
        return <label key={key}>{key==="prompt"?"장면·동작 프롬프트":"부정 프롬프트 (선택)"}<textarea maxLength={8000} required={key==="prompt"} value={values[key]} onChange={e=>field(key,e.target.value)}/><PromptWordCount text={values[key]} final/></label>;
      })}
      </div><div className="vace-input-group"><h2>생성 설정</h2><p className="vace-group-help">출력 길이와 생성 값을 확인하세요.</p><div className="vace-settings-grid">
      <label>LoRA<select value={values.lora_mode || "none"} onChange={e=>{const mode=e.target.value;setValues(old=>({...old,lora_mode:mode,...(mode!=="none"?{steps:4,guidance_scale:1,flow_shift:5}:{})}));}}><option value="none">사용 안 함</option><option value="lightning">Lightning만 · 실험</option><option value="fighting_lightning">격투 + Lightning · 실험</option></select></label>
      {[["frames","출력 프레임",5,129,4],["steps","스텝",2,100,1],["flow_shift","Flow shift",0.1,20,"any"],["guidance_scale","CFG",1,10,"any"],["reference_strength","조건 강도",0.1,2,"any"]].map(([key,label,min,max,step])=>
        <label key={key}>{label}<input type="number" required min={min} max={max} step={step} value={values[key]} onChange={e=>field(key,e.target.value===""?"":Number(e.target.value))}/></label>)}
      </div>{frameLimit!==null && <p>입력에 사용할 수 있는 최대 출력 길이 {frameLimit}프레임 <button type="button" onClick={()=>field("frames",frameLimit)}>최대 프레임 적용</button></p>}
      {invalidFrames && <p role="alert">출력 프레임이 입력 영상보다 깁니다. {frameLimit}프레임 이하로 줄이세요.</p>}
      {["lightning","fighting_lightning"].includes(values.lora_mode) && <p>Lightning은 High·Low 전문가에 적용합니다. {values.lora_mode==="fighting_lightning" && "격투 LoRA는 High 전문가에 적용합니다. "}4스텝·CFG 1·shift 5가 필요하며 동작 품질은 검수해야 합니다. {values.lora_mode==="fighting_lightning" && <><a href="/management/frame/model-management/?model=wan22-fighting-lora">격투 LoRA 준비</a> · </>}<a href="/management/frame/model-management/?model=wan22-vace-lightning">Lightning 준비</a></p>}
      <p>832×480 · 16fps · {Number(values.frames)>0?(Number(values.frames)/16).toFixed(2):"0"}초 · VACE-Fun A14B BF16 · Euler/FlowMatch</p>
      <SeedInput value={values.seed} max={template.maximum_seed} onChange={value=>field("seed",value===""?"":Number(value))}/>
      </div><ActionButton type="submit" reasons={[
        !generationReady(model) && "모델 준비 상태를 확인하세요.",
        ["lightning","fighting_lightning"].includes(values.lora_mode) && (values.steps!==4 || values.guidance_scale!==1 || values.flow_shift!==5) && "Lightning에는 4스텝·CFG 1·shift 5가 필요합니다.",
        !values.prompt.trim() && "프롬프트를 입력하세요.",
        values.mode!=="text" && !files.reference && "참조 이미지를 선택하세요.",
        attachments.some(key=>!files[key]) && "필수 영상을 선택하세요.",
        checkingVideo && "영상 정보를 확인하고 있습니다.",
        missingVideoInfo && "영상 정보를 확인하세요.",
        invalidFrames && "출력 프레임 수를 입력 영상에 맞게 조정하세요."
      ]}>생성 요청 검토</ActionButton>
    </fieldset></form></GeneratorSectionCard>}
    {pending && <section ref={reviewRef} tabIndex={-1} className="fun-request-review" aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/>
      <p>{template.modes.find(mode=>mode.id===pending.mode)?.label || pending.mode} · {pending.frames}프레임 · 16fps · {(pending.frames/16).toFixed(2)}초 · {pending.steps}스텝 · 시드 {pending.seed}</p>
      <p>Flow shift {pending.flow_shift} · CFG {pending.guidance_scale} · 조건 강도 {pending.reference_strength}</p>
      <p>LoRA · {pending.lora_mode === "fighting_lightning" ? "격투 + Lightning" : pending.lora_mode === "lightning" ? "Lightning만" : "사용 안 함"}</p>
      {pending.mode!=="text" && <p>참조 이미지 · {files.reference?.name || "선택됨"}</p>}
      {attachments.map(key=><p key={key}>{labels[key]} · {files[key]?.name || "선택됨"} · {videoInfo[key]?.summary || "영상 정보 확인 불가"}</p>)}{pending.mode==="video_edit" && <p>마스크의 편집·보존 영역은 접수 시 추가 검증합니다.</p>}
      <h3>장면·동작 프롬프트</h3><p className="fun-review-prompt">{pending.prompt}</p><h3>부정 프롬프트</h3><p className="fun-review-prompt">{pending.negative_prompt || "없음"}</p>
      {handoff.review && <p>동의하면 진행 중인 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 영상을 생성합니다. 작업이 끝나면 Qwen 3.8을 다시 GPU에 적재합니다.</p>}
      <GenerationReviewActions busy={busy} onCancel={()=>{setPending(null);handoff.clearReview();requestAnimationFrame(()=>formRef.current?.querySelector("textarea")?.focus());}} onConfirm={submit} confirmLabel={handoff.review ? "해제·생성·재적재에 동의" : undefined} disabledReason={!generationReady(model) ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : ""}/></section>}
    <fieldset className="vace-history-card" ref={historyRef} disabled={busy || !!pending}><GeneratorHistory card directApply allowPriority onSelectedDeleted={(id,message)=>{if(sourceJob===id)setSourceJob("");if(job===id) cleaned(message); else setNotice(message);}} key={historyRevision} service={service} readJob={readJob} openResult={openResult} resultId={job} onCloseResult={()=>setJob("")} restore={restore} footer={<HistoryCleanup allowSelected={false} service={service} onDeleted={cleaned}/>} renderResult={(id,close)=><section ref={node=>{resultRef.current=node;if(node && focusResult.current){focusResult.current=false;requestAnimationFrame(()=>{if(node.isConnected){node.focus();node.scrollIntoView({block:'start'});}});}}} tabIndex={-1} aria-label="선택한 VACE 작업 결과"><button type="button" onClick={close}>결과 닫기</button><SavedVaceInputs key={id} id={id}/><MediaJobResult key={id} service={service} id={id} hideProgress>
      {(record,reload)=>record && <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>}
    </MediaJobResult></section>}/></fieldset>
    {notice && <p role="status">{notice}</p>}
  </article>;
}
