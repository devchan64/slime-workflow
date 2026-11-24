import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {validVideoJobId} from "./videoJobId.mjs";
import {referencePng} from "./videoInputs.js";
import {generationReady} from "./generationReady.mjs";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorUsage from "./GeneratorUsage.jsx";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ReviewPrompt from "./ReviewPrompt.jsx";
import ActionButton from "./ActionButton.jsx";
import GeneratorSectionNavigation from "./GeneratorSectionNavigation.jsx";
import SeedInput from "./SeedInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import SavedGeneratorInputs from "./SavedGeneratorInputs.jsx";
import {generationProposalScope,readGenerationProposal} from "./generationProposal.mjs";

const service="wan22-i2v";
const polearmPrompt="A warrior grips a long spear with both hands and faces a giant armored boss. The warrior steps forward and thrusts the spear toward the boss, then pulls it back and sweeps it sideways. Wide shot, the entire spear and both hands remain visible, continuous motion, stable background.";
export default function I2VPage({embedded=false,session:embeddedSession=""}={}){
  const session=embeddedSession || new URLSearchParams(location.search).get("session") || "";
  const [settings,setSettings]=useState({prompt:"",negative_prompt:"",frames:21,steps:4,seed:42,flow_shift:5,guidance_scale:1,lora_mode:"lightning",kungfu_strength:1});
  const [file,setFile]=useState(null),[model,setModel]=useState(null),[pending,setPending]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(""),[job,setJob]=useState(new URLSearchParams(location.search).get("job") || ""),[revision,setRevision]=useState(0),[notice,setNotice]=useState("");
  const [modelError,setModelError]=useState("");
  const [imageCheckPending,setImageCheckPending]=useState(false);
  const settingErrorId=useId();
  const sending=useRef(false),formRef=useRef(null),inputCardRef=useRef(null),reviewRef=useRef(null),reviewOrigin=useRef(null),historyRef=useRef(null),resultRef=useRef(null),nonLightningSettings=useRef(null);
  const currentInput=useRef(null),imageSelectionRevision=useRef(0),imageChecking=useRef(false),promptEdited=useRef(false),reviewRequest=useRef(null);currentInput.current={settings,file,busy,pending};
  useEffect(()=>()=>{reviewRequest.current?.abort();reviewRequest.current=null;},[]);
  const usesLightning=settings.lora_mode.includes("lightning");
  const invalidFrames=!Number.isInteger(settings.frames) || settings.frames<5 || settings.frames>129 || (settings.frames-1)%4!==0;
  const invalidSteps=!Number.isInteger(settings.steps) || settings.steps<2 || settings.steps>100 || (usesLightning && settings.steps!==4);
  const invalidSeed=!Number.isInteger(settings.seed) || settings.seed<0 || settings.seed>2147483647;
  const invalidShift=!Number.isFinite(settings.flow_shift) || settings.flow_shift<0.1 || settings.flow_shift>20;
  const invalidGuidance=!Number.isFinite(settings.guidance_scale) || settings.guidance_scale<1 || settings.guidance_scale>10 || (usesLightning && settings.guidance_scale!==1);
  const reasons=[!generationReady(model) && "모델 준비 상태를 확인하세요.",imageCheckPending && "선택한 이미지 확인이 끝날 때까지 기다리세요.",!file && "첫 프레임 이미지를 선택하세요.",!settings.prompt.trim() && "동작 프롬프트를 입력하세요.",invalidFrames && "프레임은 5~129 사이의 4n+1이어야 합니다.",invalidSteps && "스텝 설정을 확인하세요.",invalidShift && "Flow shift는 0.1~20이어야 합니다.",invalidGuidance && "CFG 설정을 확인하세요.",invalidSeed && "시드는 0~2147483647의 정수여야 합니다."];
  useEffect(()=>{if(pending){if(document.activeElement===document.body || document.activeElement===reviewOrigin.current)reviewRef.current?.focus();reviewOrigin.current=null;}},[pending]);
  useEffect(()=>{
    let active=true;
    (async()=>{try{
      const scope=generationProposalScope(location.search,session,'video');
      if(!scope)return;
      const proposal=await readGenerationProposal(managementCommand,scope);
      if(proposal.service!==service || proposal.mode!=='first_frame' || !proposal.prompt.trim())throw new Error('I2V 영상 제안을 확인할 수 없습니다.');
      if(active)setSettings(old=>promptEdited.current || old.prompt ? old : {...old,prompt:proposal.prompt});
    }catch(e){if(active)setError(e.message || '대화 제안을 확인할 수 없습니다.');}})();
    return ()=>{active=false;};
  },[session]);
  function field(name,value){if(name==='prompt')promptEdited.current=true;setSettings(old=>({...old,[name]:value}));}
  async function readSavedInput(id,forRestore=true){
    const start=currentInput.current,selectionAtStart=imageSelectionRevision.current,focusAtStart=document.activeElement;
    if(forRestore && imageChecking.current)throw new Error('이미지 확인이 끝난 뒤 입력을 적용하세요.');
    if(forRestore && (start.busy || start.pending || reviewRequest.current))throw new Error('생성 요청 검토가 끝난 뒤 입력을 적용하세요.');
    const controller=new AbortController();let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      const response=await untilAborted(fetch('/management/assistant/wan22-i2v-input/'+encodeURIComponent(id),{cache:'no-store',signal:controller.signal}),controller.signal);
      if(!response.ok)throw new Error('저장 입력 또는 참조 이미지를 확인할 수 없습니다. 이력을 확인한 뒤 다시 시도하세요.');
      const record=await untilAborted(response.json(),controller.signal);
      if(record?.id!==id || !record.request || !Array.isArray(record.request.images) || record.request.images.length!==1 || typeof record.request.images[0]!=='string')throw new Error('저장 입력이 선택한 작업과 일치하지 않습니다.');
      const bytes=Uint8Array.from(atob(record.request.images[0]),character=>character.charCodeAt(0));
      return {...record,restoredFile:new File([bytes],'reference-1.png',{type:'image/png'}),inputAtStart:start,selectionAtStart,focusAtStart};
    }catch(problem){if(timedOut)throw new Error('저장 입력 조회 시간이 초과됐습니다. 다시 시도하세요.');throw problem;}
    finally{clearTimeout(timeout);}
  }
  function restoreSavedInput(request,record){
    const current=currentInput.current,start=record.inputAtStart;
    if(current.busy || current.pending || reviewRequest.current || imageChecking.current || current.settings!==start.settings || current.file!==start.file || imageSelectionRevision.current!==record.selectionAtStart)throw new Error('조회 중 입력 또는 이미지 선택이 변경되어 적용하지 않았습니다. 다시 시도하세요.');
    const {images,action,width,height,...restored}=request;
    nonLightningSettings.current=null;promptEdited.current=true;setSettings(restored);setFile(record.restoredFile);setError('');setNotice(record.id+'의 입력을 적용했습니다. 설정과 이미지를 확인하세요.');
    if(inputCardRef.current)inputCardRef.current.open=true;
    requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===record.focusAtStart){formRef.current?.focus();formRef.current?.scrollIntoView({block:'start'});}});
  }
  async function review(event){
    event.preventDefault();if(busy || pending || reviewRequest.current)return;setError("");
    const s=settings;
    if(imageChecking.current || reasons.some(Boolean)){setError("생성 입력과 설정을 확인하세요.");return;}
    const controller=new AbortController(),selection=imageSelectionRevision.current;reviewRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);reviewOrigin.current=document.activeElement;setBusy(true);
    try{const image=await untilAborted(referencePng(file),controller.signal);if(reviewRequest.current!==controller || controller.signal.aborted)return;
      if(currentInput.current.settings!==s || currentInput.current.file!==file || imageChecking.current || imageSelectionRevision.current!==selection)throw new Error("이미지 확인 중 입력이 바뀌었습니다. 다시 검토하세요.");
      setPending({action:"generate",...s,prompt:s.prompt.trim(),images:[image],width:832,height:480});}
    catch(e){if(reviewRequest.current===controller)setError(timedOut ? "이미지 확인 시간이 초과됐습니다. 다시 시도하세요." : e.message || "이미지를 읽을 수 없습니다.");}finally{clearTimeout(timer);if(reviewRequest.current===controller){reviewRequest.current=null;setBusy(false);}}
  }
  function cancelReview(){
    const restore=reviewRef.current?.contains(document.activeElement);setPending(null);
    if(inputCardRef.current)inputCardRef.current.open=true;
    if(restore)requestAnimationFrame(()=>{if(document.activeElement===document.body)(formRef.current?.querySelector('textarea') || formRef.current)?.focus();});
  }
  async function submit(){
    if(!pending || sending.current || !generationReady(model))return;
    sending.current=true;setBusy(true);setError("");setNotice("");const request=pending;
    const controller=new AbortController();let timedOut=false;const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{const result=await untilAborted(managementCommand(service,"generate",request,{signal:controller.signal}),controller.signal);if(!validVideoJobId(result?.id))throw new Error("접수 ID를 확인할 수 없습니다.");setJob(result.id);setRevision(x=>x+1);setNotice("생성 요청을 접수했습니다. 작업 이력에서 진행 상태를 확인하세요.");}
    catch(e){setError((timedOut ? "접수 응답 시간이 초과됐습니다." : e.message || "접수 여부를 확인할 수 없습니다.")+" · 접수 여부가 불확실합니다. 재접수하기 전에 이력을 확인하세요.");}
    finally{const restore=reviewRef.current?.contains(document.activeElement);clearTimeout(timer);sending.current=false;setBusy(false);setPending(null);if(restore)requestAnimationFrame(()=>{if(document.activeElement===document.body)formRef.current?.focus();});}
  }
  return <article className={"vace-page generator-page-common"+(embedded ? "" : " vace-standalone")}>
    <GeneratorPageIdentity service={service} embedded={embedded} session={session} changelogCard/>
    <GeneratorUsage generator={service}/>
    <GeneratorSectionNavigation inputRef={formRef} historyRef={historyRef} resultRef={resultRef} resultReady={Boolean(job)} openOnNavigate/>
    <GeneratorSectionCard title="모델 준비" summary={modelError ? "상태 조회 실패 · 다시 확인하세요" : !model ? "상태 확인 중" : generationReady(model) ? "준비 완료" : "준비 필요"}><ModelReadiness session={session} service={service} modelManagementService="wan22-i2v-assets" onStatus={setModel} onError={setModelError}/></GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={revision+":"+job} onOpenResult={setJob}/>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <GeneratorSectionCard title="생성 입력" summary="첫 이미지와 동작 지시" defaultOpen cardRef={inputCardRef} className="vace-input-card"><form ref={formRef} tabIndex={-1} aria-label="생성 입력" onSubmit={review}><fieldset disabled={busy || !!pending}><legend className="generator-visually-hidden">생성 입력</legend>
      <ReferenceImageInput label="첫 프레임 이미지" source={file} onSelectionStart={()=>{imageSelectionRevision.current++;}} onCheckingChange={value=>{imageChecking.current=value;setImageCheckPending(value);}} onChange={setFile} disabled={busy || !!pending}/><p>이미지는 흰 여백을 넣어 832×480으로 맞춥니다.</p>
      <label>장면·동작 프롬프트<textarea required maxLength={8000} value={settings.prompt} onChange={e=>field("prompt",e.target.value)}/><PromptWordCount text={settings.prompt} final/></label>
      <button type="button" onClick={()=>field("prompt",polearmPrompt)}>장병기 보스전 예시 입력</button><p>예시는 현재 프롬프트를 바꿉니다. 첫 이미지에 전신과 창 전체가 보이도록 구성하세요. 장병기 전용 LoRA는 아직 검증되지 않았습니다.</p>
      <label>부정 프롬프트<textarea maxLength={8000} value={settings.negative_prompt} onChange={e=>field("negative_prompt",e.target.value)}/><PromptWordCount text={settings.negative_prompt} final/></label>
      <label>LoRA<select value={settings.lora_mode} onChange={e=>{const mode=e.target.value,wasLightning=settings.lora_mode.includes("lightning"),nextLightning=mode.includes("lightning");if(!wasLightning && nextLightning)nonLightningSettings.current={steps:settings.steps,guidance_scale:settings.guidance_scale};const restored=wasLightning && !nextLightning ? nonLightningSettings.current : null;if(restored)nonLightningSettings.current=null;setSettings(old=>({...old,lora_mode:mode,...(nextLightning ? {steps:4,guidance_scale:1} : restored || {})}));}}><option value="lightning">Lightning</option><option value="none">사용 안 함</option></select></label>
      <div className="vace-settings-grid">{[["frames","프레임",5,129,4,invalidFrames,"5~129 사이에서 4프레임 간격으로 입력하세요. 예: 5, 9, 13."],["steps","스텝",2,100,1,invalidSteps,"2~100의 정수를 입력하세요. Lightning 사용 시 4여야 합니다."],["flow_shift","Flow shift",0.1,20,"any",invalidShift,"0.1~20 사이로 입력하세요."],["guidance_scale","CFG",1,10,"any",invalidGuidance,"1~10 사이로 입력하세요. Lightning 사용 시 1이어야 합니다."]].map(([key,label,min,max,step,invalid,message])=><label key={key}>{label}<input type="number" required min={min} max={max} step={step} readOnly={usesLightning && (key==="steps" || key==="guidance_scale")} aria-invalid={invalid || undefined} aria-describedby={invalid ? `${settingErrorId}-${key}` : undefined} value={settings[key]} onChange={e=>field(key,e.target.value===""?"":Number(e.target.value))}/>{invalid && <small className="vace-field-error" id={`${settingErrorId}-${key}`}>{message}</small>}{key==="frames" && !invalid && <small>5~129, 4프레임 간격 · 16fps</small>}</label>)}</div>
      <SeedInput value={settings.seed} max={2147483647} error={invalidSeed ? "0~2147483647의 정수를 입력하세요." : ""} onChange={value=>field("seed",value===""?"":Number(value))}/>
      <p>832×480 · 16fps · 예상 재생 길이 {invalidFrames ? "계산 불가" : `${(settings.frames/16).toFixed(2)}초`}{usesLightning && " · Lightning 4스텝·CFG 1 고정"}. 동작 품질은 검수해야 합니다.</p>
      <ActionButton type="submit" reasons={reasons}>생성 요청 검토</ActionButton>
    </fieldset></form></GeneratorSectionCard>
    {pending && <section ref={reviewRef} tabIndex={-1} className="fun-request-review" aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/><p>{file?.name} · 832×480 · {pending.frames}프레임 · 16fps · {pending.steps}스텝 · 시드 {pending.seed}</p><p>LoRA {pending.lora_mode} · Flow shift {pending.flow_shift} · CFG {pending.guidance_scale}</p><ReviewPrompt label="장면·동작 프롬프트" text={pending.prompt}/><ReviewPrompt label="부정 프롬프트" text={pending.negative_prompt}/><GenerationReviewActions busy={busy} disabledReason={!generationReady(model) ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : ""} onCancel={cancelReview} onConfirm={submit}/></section>}
    <div ref={historyRef} tabIndex={-1}><GeneratorHistory key={revision} service={service} statusCommand="status" card allowPriority readJob={readSavedInput} restore={restoreSavedInput} openResult={setJob} resultId={job} onCloseResult={()=>setJob("")} onSelectedDeleted={(id,message)=>{if(job===id)setJob("");setNotice(message);setRevision(x=>x+1);}} footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={message=>{setJob("");setNotice(message);setRevision(x=>x+1);}}/>} renderResult={(id,close)=><section ref={resultRef} tabIndex={-1}><button type="button" onClick={close}>결과 닫기</button><SavedGeneratorInputs id={id} service={service} readJob={currentId=>readSavedInput(currentId,false)}/><MediaJobResult service={service} id={id}>{(record,reload)=>record && <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>}</MediaJobResult></section>}/></div>
  </article>;
}
