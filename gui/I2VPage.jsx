import React,{useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
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
import ActionButton from "./ActionButton.jsx";
import GeneratorSectionNavigation from "./GeneratorSectionNavigation.jsx";
import SeedInput from "./SeedInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import {generationProposalScope,readGenerationProposal} from "./generationProposal.mjs";

const service="wan22-i2v";
const kungfuWarning="주의: 한손검 비교 실험에서 KungFu 적용 시 무술 동작과 회전이 늘고 마지막에 검이 흐려졌습니다. 한 번의 실험 결과이며, 검술·무기 동작에서는 결과를 확인하세요.";
const polearmPrompt="A warrior grips a long spear with both hands and faces a giant armored boss. The warrior steps forward and thrusts the spear toward the boss, then pulls it back and sweeps it sideways. Wide shot, the entire spear and both hands remain visible, continuous motion, stable background.";
export default function I2VPage({embedded=false,session:embeddedSession=""}={}){
  const session=embeddedSession || new URLSearchParams(location.search).get("session") || "";
  const [settings,setSettings]=useState({prompt:"",negative_prompt:"",frames:21,steps:4,seed:42,flow_shift:5,guidance_scale:1,lora_mode:"lightning",kungfu_strength:1});
  const [file,setFile]=useState(null),[model,setModel]=useState(null),[pending,setPending]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(""),[job,setJob]=useState(new URLSearchParams(location.search).get("job") || ""),[revision,setRevision]=useState(0),[notice,setNotice]=useState("");
  const sending=useRef(false),formRef=useRef(null),reviewRef=useRef(null),historyRef=useRef(null),resultRef=useRef(null),nonLightningSettings=useRef(null);
  const usesLightning=settings.lora_mode.includes("lightning"),usesKungfu=settings.lora_mode.includes("kungfu");
  const invalidFrames=!Number.isInteger(settings.frames) || settings.frames<5 || settings.frames>129 || (settings.frames-1)%4!==0;
  const invalidSteps=!Number.isInteger(settings.steps) || settings.steps<2 || settings.steps>100 || (usesLightning && settings.steps!==4);
  const invalidSeed=!Number.isInteger(settings.seed) || settings.seed<0 || settings.seed>2147483647;
  const invalidShift=!Number.isFinite(settings.flow_shift) || settings.flow_shift<0.1 || settings.flow_shift>20;
  const invalidGuidance=!Number.isFinite(settings.guidance_scale) || settings.guidance_scale<1 || settings.guidance_scale>10 || (usesLightning && settings.guidance_scale!==1);
  const invalidStrength=!Number.isFinite(settings.kungfu_strength) || settings.kungfu_strength<0 || settings.kungfu_strength>2 || (usesKungfu && settings.kungfu_strength<=0);
  const reasons=[!generationReady(model) && "모델 준비 상태를 확인하세요.",!file && "첫 프레임 이미지를 선택하세요.",!settings.prompt.trim() && "동작 프롬프트를 입력하세요.",invalidFrames && "프레임은 5~129 사이의 4n+1이어야 합니다.",invalidSteps && "스텝 설정을 확인하세요.",invalidShift && "Flow shift는 0.1~20이어야 합니다.",invalidGuidance && "CFG 설정을 확인하세요.",invalidStrength && "KungFu 강도를 확인하세요.",invalidSeed && "시드는 0~2147483647의 정수여야 합니다."];
  useEffect(()=>{if(pending)reviewRef.current?.focus();},[pending]);
  useEffect(()=>{
    let active=true;
    (async()=>{try{
      const scope=generationProposalScope(location.search,session,'video');
      if(!scope)return;
      const proposal=await readGenerationProposal(managementCommand,scope);
      if(proposal.service!==service || proposal.mode!=='first_frame' || !proposal.prompt.trim())throw new Error('I2V 영상 제안을 확인할 수 없습니다.');
      if(active)setSettings(old=>old.prompt ? old : {...old,prompt:proposal.prompt});
    }catch(e){if(active)setError(e.message || '대화 제안을 확인할 수 없습니다.');}})();
    return ()=>{active=false;};
  },[session]);
  function field(name,value){setSettings(old=>({...old,[name]:value}));}
  async function review(event){
    event.preventDefault();if(busy || pending)return;setError("");
    const s=settings;
    if(reasons.some(Boolean)){setError("생성 입력과 설정을 확인하세요.");return;}
    setBusy(true);
    try{const image=await referencePng(file);setPending({action:"generate",...s,prompt:s.prompt.trim(),images:[image],width:832,height:480});}
    catch(e){setError(e.message || "이미지를 읽을 수 없습니다.");}finally{setBusy(false);}
  }
  async function submit(){
    if(!pending || sending.current || !generationReady(model))return;
    sending.current=true;setBusy(true);setError("");const request=pending;setPending(null);
    try{const result=await managementCommand(service,"generate",request);if(!result.id)throw new Error("접수 ID를 확인할 수 없습니다.");setJob(result.id);setRevision(x=>x+1);}
    catch(e){setError((e.message || "접수 실패")+" · 다시 접수하기 전에 이력을 확인하세요.");}
    finally{sending.current=false;setBusy(false);}
  }
  return <article className="vace-page generator-page-common vace-standalone">
    <GeneratorPageIdentity service={service} embedded={embedded} session={session} changelogCard/>
    <GeneratorUsage generator={service}/>
    <GeneratorSectionNavigation inputRef={formRef} historyRef={historyRef} resultRef={resultRef} resultReady={Boolean(job)} openOnNavigate/>
    <GeneratorSectionCard title="모델 준비" summary="I2V 본체와 LoRA"><ModelReadiness service={service} modelManagementService="wan22-i2v-assets" onStatus={setModel}/></GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={revision+":"+job} onOpenResult={setJob}/>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <GeneratorSectionCard title="생성 입력" summary="첫 이미지와 동작 지시" defaultOpen><form ref={formRef} tabIndex={-1} aria-label="생성 입력" onSubmit={review}><fieldset disabled={busy || !!pending}>
      <ReferenceImageInput label="첫 프레임 이미지" source={file} onChange={setFile} disabled={busy || !!pending}/><p>이미지는 흰 여백을 넣어 832×480으로 맞춥니다.</p>
      <label>장면·동작 프롬프트<textarea required maxLength={8000} value={settings.prompt} onChange={e=>field("prompt",e.target.value)}/><PromptWordCount text={settings.prompt} final/></label>
      <button type="button" onClick={()=>field("prompt",polearmPrompt)}>장병기 보스전 예시 입력</button><p>예시는 현재 프롬프트를 바꿉니다. 첫 이미지에 전신과 창 전체가 보이도록 구성하세요. 장병기 전용 LoRA는 아직 검증되지 않았습니다.</p>
      <label>부정 프롬프트<textarea maxLength={8000} value={settings.negative_prompt} onChange={e=>field("negative_prompt",e.target.value)}/><PromptWordCount text={settings.negative_prompt} final/></label>
      <label>LoRA<select value={settings.lora_mode} onChange={e=>{const mode=e.target.value,wasLightning=settings.lora_mode.includes("lightning"),nextLightning=mode.includes("lightning");if(!wasLightning && nextLightning)nonLightningSettings.current={steps:settings.steps,guidance_scale:settings.guidance_scale};const restored=wasLightning && !nextLightning ? nonLightningSettings.current : null;if(restored)nonLightningSettings.current=null;setSettings(old=>({...old,lora_mode:mode,...(nextLightning ? {steps:4,guidance_scale:1} : restored || {}),...(!mode.includes("kungfu") && (!Number.isFinite(old.kungfu_strength) || old.kungfu_strength<0 || old.kungfu_strength>2) ? {kungfu_strength:1} : {})}));}}><option value="lightning">Lightning</option><option value="lightning_kungfu">Lightning + KungFu</option><option value="kungfu">KungFu</option><option value="none">사용 안 함</option></select></label>
      {settings.lora_mode.includes("kungfu") && <p role="alert">{kungfuWarning}</p>}
      <div className="vace-settings-grid">{[["frames","프레임",5,129,4,invalidFrames],["steps","스텝",2,100,1,invalidSteps],["flow_shift","Flow shift",0.1,20,"any",invalidShift],["guidance_scale","CFG",1,10,"any",invalidGuidance],...(usesKungfu ? [["kungfu_strength","KungFu 강도",0,2,"any",invalidStrength]] : [])].map(([key,label,min,max,step,invalid])=><label key={key}>{label}<input type="number" required min={min} max={max} step={step} readOnly={usesLightning && (key==="steps" || key==="guidance_scale")} aria-invalid={invalid || undefined} value={settings[key]} onChange={e=>field(key,e.target.value===""?"":Number(e.target.value))}/>{key==="frames" && <small>5~129, 4프레임 간격 · 16fps</small>}</label>)}</div>
      <SeedInput value={settings.seed} max={2147483647} error={invalidSeed ? "0~2147483647의 정수를 입력하세요." : ""} onChange={value=>field("seed",value===""?"":Number(value))}/>
      <p>832×480 · 16fps · {Number.isInteger(settings.frames) && settings.frames>0 ? (settings.frames/16).toFixed(2) : "0"}초{usesLightning && " · Lightning 4스텝·CFG 1 고정"}{usesKungfu && " · KungFu 트리거: wugong"}. 동작 품질은 검수해야 합니다.</p>
      <ActionButton type="submit" reasons={reasons}>생성 요청 검토</ActionButton>
    </fieldset></form></GeneratorSectionCard>
    {pending && <section ref={reviewRef} tabIndex={-1} className="fun-request-review" aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/><p>{file?.name} · 832×480 · {pending.frames}프레임 · 16fps · {pending.steps}스텝 · 시드 {pending.seed}</p><p>LoRA {pending.lora_mode} · Flow shift {pending.flow_shift} · CFG {pending.guidance_scale}{pending.lora_mode.includes("kungfu") && ` · KungFu 강도 ${pending.kungfu_strength}`}</p>{pending.lora_mode.includes("kungfu") && <p>{kungfuWarning}</p>}<p>{pending.prompt}</p><p>부정 프롬프트: {pending.negative_prompt || "없음"}</p><GenerationReviewActions busy={busy} onCancel={()=>{setPending(null);requestAnimationFrame(()=>formRef.current?.querySelector("textarea")?.focus());}} onConfirm={submit}/></section>}
    <div ref={historyRef} tabIndex={-1}><GeneratorHistory key={revision} service={service} statusCommand="status" card allowPriority openResult={setJob} resultId={job} onCloseResult={()=>setJob("")} onSelectedDeleted={(id,message)=>{if(job===id)setJob("");setNotice(message);setRevision(x=>x+1);}} footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={message=>{setJob("");setNotice(message);setRevision(x=>x+1);}}/>} renderResult={(id,close)=><section ref={resultRef} tabIndex={-1}><button type="button" onClick={close}>결과 닫기</button><MediaJobResult service={service} id={id}>{(record,reload)=>record && <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>}</MediaJobResult></section>}/></div>
  </article>;
}
