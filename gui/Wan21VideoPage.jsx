import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {validVideoJobId} from "./videoJobId.mjs";
import {referencePng} from "./videoInputs.js";
import {generationReady,modelFilesReady} from "./generationReady.mjs";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorUsage from "./GeneratorUsage.jsx";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import GeneratorSectionNavigation from "./GeneratorSectionNavigation.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ReviewPrompt from "./ReviewPrompt.jsx";
import SeedInput from "./SeedInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import ActionButton from "./ActionButton.jsx";
import SavedGeneratorInputs from "./SavedGeneratorInputs.jsx";
import {generationProposalScope,readGenerationProposal,wan21ProposalInputs} from "./generationProposal.mjs";

function Wan21VideoPage({mode,embedded=false,session:embeddedSession=""}) {
  const session=embeddedSession || new URLSearchParams(location.search).get("session") || "";
  const service=`wan21-${mode}`, isImage=mode==="i2v";
  const [settings,setSettings]=useState({prompt:"",negative_prompt:"",frames:21,steps:4,seed:42,flow_shift:5,guidance_scale:1,acceleration:true,action_lora:false,action_variant:"fight",action_strength:1});
  const [file,setFile]=useState(null), [model,setModel]=useState(null), [pending,setPending]=useState(null), [busy,setBusy]=useState(false), [error,setError]=useState(""), [job,setJob]=useState(""), [revision,setRevision]=useState(0), [notice,setNotice]=useState("");
  const [modelError,setModelError]=useState("");
  const [imageCheckPending,setImageCheckPending]=useState(false);
  const [attackModel,setAttackModel]=useState(null), [attackError,setAttackError]=useState("");
  const settingErrorId=useId();
  const sending=useRef(false);
  const formRef=useRef(null), inputCardRef=useRef(null), reviewRef=useRef(null), reviewOrigin=useRef(null), historyRef=useRef(null), resultRef=useRef(null), currentInput=useRef(null), imageSelectionRevision=useRef(0), imageChecking=useRef(false), promptEdited=useRef(false), reviewRequest=useRef(null);
  currentInput.current={settings,file,busy,pending};
  useEffect(()=>()=>{reviewRequest.current?.abort();reviewRequest.current=null;},[]);
  const invalidFrames=!Number.isInteger(settings.frames) || settings.frames<5 || settings.frames>129 || (settings.frames-1)%4!==0;
  const invalidSteps=!Number.isInteger(settings.steps) || settings.steps<2 || settings.steps>100 || (settings.acceleration && settings.steps!==4);
  const invalidSeed=!Number.isInteger(settings.seed) || settings.seed<0 || settings.seed>2147483647;
  const invalidShift=!Number.isFinite(settings.flow_shift) || settings.flow_shift<0.1 || settings.flow_shift>20;
  const invalidGuidance=!Number.isFinite(settings.guidance_scale) || settings.guidance_scale<1 || settings.guidance_scale>10 || (settings.acceleration && settings.guidance_scale!==1);
  const invalidStrength=!Number.isFinite(settings.action_strength) || settings.action_strength<0 || settings.action_strength>2 || (settings.action_lora && settings.action_strength<=0);
  const usesAttack=isImage && settings.action_lora && ["attack_high","attack_low"].includes(settings.action_variant);
  const attackReason=usesAttack && !modelFilesReady(attackModel) ? (attackError ? "공격 LoRA 상태 조회에 실패했습니다. 모델 준비에서 다시 확인하세요." : !attackModel ? "공격 LoRA 준비 상태를 확인하고 있습니다." : "공격 LoRA를 준비하거나 다른 동작을 선택하세요.") : "";
  const inputReasons=[!model ? "모델 준비 상태를 확인하세요." : !generationReady(model) ? "모델 준비 상태와 오류를 확인하세요." : "", isImage && imageCheckPending && "선택한 이미지 확인이 끝날 때까지 기다리세요.", isImage && !file ? "첫 프레임 이미지를 선택하세요." : "", !settings.prompt.trim() ? "프롬프트를 입력하세요." : "", !isImage && settings.action_lora && !model?.boss_lora_available && "KXSR 파일을 준비하거나 동작 LoRA를 끄세요.", attackReason, invalidFrames && "프레임은 5~129 사이의 4n+1이어야 합니다.", invalidSteps && "스텝은 2~100의 정수이며 가속 사용 시 4여야 합니다.", invalidShift && "Flow shift는 0.1~20이어야 합니다.", invalidGuidance && "CFG는 1~10이며 가속 사용 시 1이어야 합니다.", invalidSeed && "시드는 0~2147483647의 정수여야 합니다.", invalidStrength && "동작 LoRA 강도는 0~2이며 사용 시 0보다 커야 합니다."];
  useEffect(()=>{
    if(!pending)return;
    if(document.activeElement===document.body || document.activeElement===reviewOrigin.current)reviewRef.current?.focus();
    reviewOrigin.current=null;
  },[pending]);
  useEffect(()=>{
    let active=true;
    (async()=>{try{
      const scope=generationProposalScope(location.search,session,'video');
      if(!scope)return;
      const proposal=await readGenerationProposal(managementCommand,scope);
      const inputs=wan21ProposalInputs({},proposal,service);
      if(active)setSettings(old=>promptEdited.current || old.prompt ? old : {...old,prompt:inputs.prompt});
    }catch(e){if(active)setError(e.message || '대화 제안을 확인할 수 없습니다.');}})();
    return ()=>{active=false;};
  },[service,session]);
  function field(name,value){if(name==='prompt')promptEdited.current=true;setSettings(old=>({...old,[name]:value}));}
  async function readSavedInput(id,forRestore=true){
    const start=currentInput.current, selectionAtStart=imageSelectionRevision.current, focusAtStart=document.activeElement;
    if(forRestore && imageChecking.current)throw new Error('이미지 확인이 끝난 뒤 입력을 적용하세요.');
    if(forRestore && (start.busy || start.pending || reviewRequest.current))throw new Error('생성 요청 검토가 끝난 뒤 입력을 적용하세요.');
    const controller=new AbortController();let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      const response=await untilAborted(fetch('/management/assistant/wan21-i2v-input/'+encodeURIComponent(id),{cache:'no-store',signal:controller.signal}),controller.signal);
      if(!response.ok)throw new Error('저장 입력 또는 참조 이미지를 확인할 수 없습니다. 이력을 확인한 뒤 다시 시도하세요.');
      const record=await untilAborted(response.json(),controller.signal);
      if(record?.id!==id || !record.request || !Array.isArray(record.request.images) || record.request.images.length!==1 || typeof record.request.images[0]!=='string')throw new Error('저장 입력이 선택한 작업과 일치하지 않습니다.');
      const bytes=Uint8Array.from(atob(record.request.images[0]),c=>c.charCodeAt(0));
      return {...record,restoredFile:new File([bytes],'reference-1.png',{type:'image/png'}),inputAtStart:start,selectionAtStart,focusAtStart};
    }catch(problem){if(timedOut)throw new Error('저장 입력 조회 시간이 초과됐습니다. 다시 시도하세요.');throw problem;}
    finally{clearTimeout(timeout);}
  }
  function restoreSavedInput(request,record){
    const current=currentInput.current, start=record.inputAtStart;
    if(current.busy || current.pending || reviewRequest.current || imageChecking.current || current.settings!==start.settings || current.file!==start.file || imageSelectionRevision.current!==record.selectionAtStart)throw new Error('조회 중 입력 또는 이미지 선택이 변경되어 적용하지 않았습니다. 다시 시도하세요.');
    const {images,action,width,height,...restored}=request;
    if(!usesAttack){setAttackModel(null);setAttackError('');}promptEdited.current=true;setSettings({...restored,action_variant:restored.action_variant || 'fight'});setFile(record.restoredFile);setError('');setNotice(record.id+'의 입력을 적용했습니다. 설정과 이미지를 확인하세요.');
    if(inputCardRef.current)inputCardRef.current.open=true;
    requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===record.focusAtStart){formRef.current?.focus();formRef.current?.scrollIntoView({block:'start'});}});
  }
  async function review(event){
    event.preventDefault(); if(busy || pending || reviewRequest.current)return; setError(""); const s=settings;
    if(imageChecking.current || inputReasons.some(Boolean)){setError("생성 입력과 설정을 확인하세요.");return;}
    const controller=new AbortController(),selection=imageSelectionRevision.current;reviewRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);reviewOrigin.current=document.activeElement;setBusy(true);
    try {const images=isImage?[await untilAborted(referencePng(file),controller.signal)]:[];if(reviewRequest.current!==controller || controller.signal.aborted)return;
      if(currentInput.current.settings!==s || currentInput.current.file!==file || imageChecking.current || imageSelectionRevision.current!==selection)throw new Error("입력 확인 중 설정이 바뀌었습니다. 다시 검토하세요.");
      setPending({action:"generate",...s,prompt:s.prompt.trim(),images,width:832,height:480});}
    catch(e){if(reviewRequest.current===controller)setError(timedOut ? "입력 확인 시간이 초과됐습니다. 다시 시도하세요." : e.message || "입력을 읽을 수 없습니다.");} finally {clearTimeout(timer);if(reviewRequest.current===controller){reviewRequest.current=null;setBusy(false);}}
  }
  function cancelReview(){
    const restore=reviewRef.current?.contains(document.activeElement);setPending(null);
    if(inputCardRef.current)inputCardRef.current.open=true;
    if(restore)requestAnimationFrame(()=>{if(document.activeElement===document.body){const button=formRef.current?.querySelector('button[type="submit"]');(button && !button.disabled ? button : formRef.current)?.focus();}});
  }
  async function submit(){
    if(!pending || sending.current || !generationReady(model) || attackReason || (!isImage && pending.action_lora && !model?.boss_lora_available))return;
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
    <GeneratorSectionCard title="모델 준비" summary={modelError || (usesAttack && attackError) ? "상태 조회 실패 · 다시 확인하세요" : !model || (usesAttack && !attackModel) ? "상태 확인 중" : generationReady(model) && (!usesAttack || modelFilesReady(attackModel)) ? "준비 완료" : "준비 필요"}>
      <ModelReadiness session={session} service={service} modelManagementService={`${service}-assets`} onStatus={setModel} onError={setModelError}/>
      {usesAttack && <><h3>공격 동작 LoRA</h3><ModelReadiness session={session} service="wan21-i2v-attack-lora" onStatus={setAttackModel} onError={setAttackError}/></>}
    </GeneratorSectionCard>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <GeneratorSectionCard title="생성 입력" summary={isImage?"첫 이미지와 동작":"프롬프트"} defaultOpen cardRef={inputCardRef} className="vace-input-card"><form ref={formRef} tabIndex={-1} aria-label="생성 입력" onSubmit={review}><fieldset disabled={busy || !!pending}><legend className="generator-visually-hidden">생성 입력</legend>
      {isImage && <><ReferenceImageInput label="첫 프레임 이미지" source={file} onSelectionStart={()=>{imageSelectionRevision.current++;}} onCheckingChange={value=>{imageChecking.current=value;setImageCheckPending(value);}} onChange={setFile} disabled={busy || !!pending}/><p>이미지 파일을 선택하세요. 이미지는 흰 여백을 넣어 832×480으로 맞춥니다.</p></>}
      <label>프롬프트<textarea required maxLength={8000} value={settings.prompt} onChange={e=>field("prompt",e.target.value)}/><PromptWordCount text={settings.prompt} final/></label>
      <label>부정 프롬프트<textarea maxLength={8000} value={settings.negative_prompt} onChange={e=>field("negative_prompt",e.target.value)}/></label>
      <label><input type="checkbox" checked={settings.acceleration} onChange={e=>setSettings(old=>({...old,acceleration:e.target.checked,...(e.target.checked?{steps:4,guidance_scale:1}:{})}))}/> 4스텝 가속 LoRA</label>
      {!isImage && <><label><input type="checkbox" checked={settings.action_lora} disabled={!model?.boss_lora_available && !settings.action_lora} onChange={e=>{const enabled=e.target.checked;setSettings(old=>({...old,action_lora:enabled,...(!enabled && (!Number.isFinite(old.action_strength) || old.action_strength<0 || old.action_strength>2) ? {action_strength:1} : {})}));}}/> KXSR Boss Fight LoRA</label>
      {!settings.action_lora && <p>동작 LoRA를 켜면 관련 설정을 사용할 수 있습니다.</p>}
      <p>{`KXSR 파일은 .model/wan21-t2v/action/kxsr.safetensors에 별도로 준비해야 하며 트리거는 kxsr입니다. ${model?.boss_lora_available ? "파일 해시 확인 완료." : "파일이 없거나 해시가 일치하지 않습니다."} 가속 LoRA와 KXSR 조합은 아직 검증되지 않았습니다.`}</p></>}
      {isImage && <><label>동작 LoRA<select value={settings.action_lora ? settings.action_variant : "none"} onChange={e=>{const variant=e.target.value;if(!usesAttack && ["attack_high","attack_low"].includes(variant)){setAttackModel(null);setAttackError("");}setSettings(old=>({...old,action_lora:variant!=="none",action_variant:variant==="none" ? old.action_variant : variant,...(variant==="none" && (!Number.isFinite(old.action_strength) || old.action_strength<0 || old.action_strength>2) ? {action_strength:1} : {})}));}}><option value="none">사용 안 함</option><option value="fight">Fight</option><option value="attack_high">Attack Sprite high</option><option value="attack_low">Attack Sprite low</option></select></label><p>Attack Sprite는 별도 모델 준비가 필요한 실험 옵션입니다. 동작 품질과 호환성을 결과에서 확인하세요.</p></>}
      <div className="vace-settings-grid">{[["frames","프레임",5,129,4,invalidFrames,"5~129 사이에서 4프레임 간격으로 입력하세요. 예: 5, 9, 13."],["steps","스텝",2,100,1,invalidSteps,"2~100의 정수를 입력하세요. 가속 사용 시 4여야 합니다."],["flow_shift","Flow shift",0.1,20,"any",invalidShift,"0.1~20 사이로 입력하세요."],["guidance_scale","CFG",1,10,"any",invalidGuidance,"1~10 사이로 입력하세요. 가속 사용 시 1이어야 합니다."],["action_strength","동작 LoRA 강도",0,2,"any",invalidStrength,"사용 시 0보다 크고 2 이하로 입력하세요."]].map(([key,label,min,max,step,invalid,message])=><label key={key}>{label}<input type="number" required disabled={key==="action_strength" && !settings.action_lora} min={min} max={max} step={step} aria-invalid={invalid || undefined} aria-describedby={invalid ? `${settingErrorId}-${key}` : undefined} value={settings[key]} onChange={e=>field(key,e.target.value===""?"":Number(e.target.value))}/>{invalid && <small className="vace-field-error" id={`${settingErrorId}-${key}`}>{message}</small>}</label>)}</div>
      <SeedInput value={settings.seed} max={2147483647} error={invalidSeed ? "0~2147483647의 정수를 입력하세요." : ""} onChange={value=>field("seed",value===""?"":Number(value))}/>
      <p>832×480 · 16fps · 예상 재생 길이 {Number.isFinite(settings.frames) && settings.frames>0 ? `${(settings.frames/16).toFixed(2)}초` : "계산 불가"} · 가속 사용 시 4스텝과 CFG 1. 제한된 GPU 시험을 완료했으며 출력 품질은 입력과 설정에 따라 달라집니다.</p>
      <ActionButton type="submit" reasons={inputReasons}>생성 요청 검토</ActionButton>
    </fieldset></form></GeneratorSectionCard>
    {pending && <section ref={reviewRef} tabIndex={-1} className="fun-request-review" aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/><p>{isImage && file?.name} · 832×480 · {pending.frames}프레임 · {pending.steps}스텝 · 시드 {pending.seed} · CFG {pending.guidance_scale} · Shift {pending.flow_shift}</p><p>가속 LoRA: {pending.acceleration ? "사용" : "사용 안 함"} · 동작 LoRA: {pending.action_lora ? `${isImage ? pending.action_variant : "KXSR"} (강도 ${pending.action_strength})` : "사용 안 함"}</p><ReviewPrompt label="장면·동작 프롬프트" text={pending.prompt}/><ReviewPrompt label="부정 프롬프트" text={pending.negative_prompt}/><GenerationReviewActions busy={busy} disabledReason={!generationReady(model) ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : !isImage && pending.action_lora && !model?.boss_lora_available ? "KXSR 파일을 준비하거나 입력 수정에서 동작 LoRA를 끄세요." : attackReason} onCancel={cancelReview} onConfirm={submit}/></section>}
    <ActiveGeneratorProgress service={service} revision={revision+":"+job} onOpenResult={setJob}/>
    <div ref={historyRef} tabIndex={-1}><GeneratorHistory allowPriority toggleResult key={revision} service={service} statusCommand="status" card readJob={isImage?readSavedInput:undefined} restore={isImage?restoreSavedInput:undefined} openResult={setJob} resultId={job} onCloseResult={()=>setJob("")} onSelectedDeleted={(id,message)=>{if(job===id)setJob("");setNotice(message);setRevision(x=>x+1);}} footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={message=>{setJob("");setNotice(message);setRevision(x=>x+1);}}/>} renderResult={(id,close)=><section ref={resultRef} tabIndex={-1} aria-label="선택한 작업 결과"><button type="button" onClick={close}>결과 닫기</button><SavedGeneratorInputs id={id} service={service} statusCommand="status" readJob={isImage ? currentId=>readSavedInput(currentId,false) : undefined}/><MediaJobResult service={service} id={id}>{(record,reload)=>record && <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>}</MediaJobResult></section>}/></div>
  </article>;
}
export function Wan21T2VPage(props){return <Wan21VideoPage {...props} mode="t2v"/>;}
export function Wan21I2VPage(props){return <Wan21VideoPage {...props} mode="i2v"/>;}
