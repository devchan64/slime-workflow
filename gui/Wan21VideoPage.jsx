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
  const sending=useRef(false);
  const inputReasons=[!model ? "모델 준비 상태를 확인하세요." : !generationReady(model) ? "모델 준비 상태와 오류를 확인하세요." : "", isImage && !file ? "첫 프레임 이미지를 선택하세요." : "", !settings.prompt.trim() ? "프롬프트를 입력하세요." : ""];
  useEffect(()=>{
    let active=true;
    (async()=>{try{
      const scope=generationProposalScope(location.search,session,'video');
      if(!scope)return;
      const proposal=await readGenerationProposal(managementCommand,scope);
      const inputs=wan21ProposalInputs({},proposal,service);
      if(active)setSettings(old=>old.prompt ? old : {...old,prompt:inputs.prompt});
    }catch(e){if(active)setError(e.message || '대화 제안을 확인할 수 없습니다.');}})();
    return ()=>{active=false;};
  },[service,session]);
  function field(name,value){setSettings(old=>({...old,[name]:value}));}
  async function review(event){
    event.preventDefault(); if(busy || pending)return; setError(""); const s=settings;
    if(!generationReady(model) || (isImage && !file) || !s.prompt.trim() || !Number.isInteger(s.frames) || s.frames<5 || s.frames>129 || (s.frames-1)%4 || !Number.isInteger(s.steps) || s.steps<2 || s.steps>100 || !Number.isInteger(s.seed) || s.seed<0 || s.seed>2147483647 || !Number.isFinite(s.flow_shift) || s.flow_shift<0.1 || s.flow_shift>20 || !Number.isFinite(s.guidance_scale) || s.guidance_scale<1 || s.guidance_scale>10 || !Number.isFinite(s.action_strength) || s.action_strength<0 || s.action_strength>2 || (s.action_lora && s.action_strength<=0) || (s.acceleration && (s.steps!==4 || s.guidance_scale!==1))){setError("이미지와 프롬프트, 생성 설정을 확인하세요.");return;}
    setBusy(true);
    try {const images=isImage?[await referencePng(file)]:[];setPending({action:"generate",...s,prompt:s.prompt.trim(),images,width:832,height:480});}
    catch(e){setError(e.message || "입력을 읽을 수 없습니다.");} finally {setBusy(false);}
  }
  async function submit(){
    if(!pending || sending.current || !generationReady(model))return;
    sending.current=true;setBusy(true);setError("");const request=pending;setPending(null);
    try {const result=await managementCommand(service,"generate",request);if(!result.id)throw new Error("접수 ID를 확인할 수 없습니다.");setJob(result.id);setRevision(x=>x+1);}
    catch(e){setError((e.message || "접수 실패")+" · 다시 접수하기 전에 이력을 확인하세요.");}
    finally {sending.current=false;setBusy(false);}
  }
  return <article className="vace-page generator-page-common vace-standalone">
    <GeneratorPageIdentity service={service} embedded={embedded} session={session} changelogCard/>
    <GeneratorUsage generator={service}/>
    <ModelReadiness service={service} modelManagementService={`${service}-assets`} onStatus={setModel}/>
    {isImage && <GeneratorSectionCard title="공격 LoRA 준비" summary="2.2 학습 파일 · 2.1 적용 실험"><ModelReadiness service="wan21-i2v-attack-lora" manage/></GeneratorSectionCard>}
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <GeneratorSectionCard title="생성 입력" summary={isImage?"첫 이미지와 동작":"프롬프트"} defaultOpen><form onSubmit={review}><fieldset disabled={busy || !!pending}>
      {isImage && <><ReferenceImageInput label="첫 프레임 이미지" source={file} onChange={setFile} disabled={busy || !!pending}/><p>이미지 파일을 선택하세요. 이미지는 흰 여백을 넣어 832×480으로 맞춥니다.</p></>}
      <label>프롬프트<textarea required maxLength={8000} value={settings.prompt} onChange={e=>field("prompt",e.target.value)}/><PromptWordCount text={settings.prompt} final/></label>
      <label>부정 프롬프트<textarea maxLength={8000} value={settings.negative_prompt} onChange={e=>field("negative_prompt",e.target.value)}/></label>
      <label><input type="checkbox" checked={settings.acceleration} onChange={e=>setSettings(old=>({...old,acceleration:e.target.checked,...(e.target.checked?{steps:4,guidance_scale:1}:{})}))}/> 4스텝 가속 LoRA</label>
      <label><input type="checkbox" checked={settings.action_lora} disabled={!isImage && !model?.boss_lora_available} onChange={e=>field("action_lora",e.target.checked)}/> {isImage?"동작 LoRA 사용":"KXSR Boss Fight LoRA"}</label>
      {isImage && <label>동작 LoRA<select disabled={!settings.action_lora} value={settings.action_variant} onChange={e=>field("action_variant",e.target.value)}><option value="fight">Fight · 맨손 격투</option><option value="attack_high">Attack Sprite · High (실험)</option><option value="attack_low">Attack Sprite · Low (실험)</option></select></label>}
      {!settings.action_lora && <p>동작 LoRA를 켜면 관련 설정을 사용할 수 있습니다.</p>}
      <p>{isImage?"Fight는 720p 맨손 격투용이며, Attack Sprite는 창 공격 예시가 있는 2.2 학습 모델입니다. 2.1과 가속 LoRA를 함께 사용한 제한된 시험에서 창 방향이 바뀌거나 창끝이 가려졌습니다. 무기 동작 품질은 보장되지 않습니다.":`KXSR 파일은 .model/wan21-t2v/action/kxsr.safetensors에 별도로 준비해야 하며 트리거는 kxsr입니다. ${model?.boss_lora_available ? "파일 해시 확인 완료." : "파일이 없거나 해시가 일치하지 않습니다."} 가속 LoRA와 KXSR 조합은 아직 검증되지 않았습니다.`}</p>
      <div className="vace-settings-grid">{[["frames","프레임",5,129,4],["steps","스텝",2,100,1],["flow_shift","Flow shift",0.1,20,"any"],["guidance_scale","CFG",1,10,"any"],["action_strength","동작 LoRA 강도",0,2,"any"]].map(([key,label,min,max,step])=><label key={key}>{label}<input type="number" required disabled={key==="action_strength" && !settings.action_lora} min={min} max={max} step={step} value={settings[key]} onChange={e=>field(key,e.target.value===""?"":Number(e.target.value))}/></label>)}</div>
      <SeedInput value={settings.seed} max={2147483647} onChange={value=>field("seed",value===""?"":Number(value))}/>
      <p>832×480 · 16fps · 예상 재생 길이 {Number.isFinite(settings.frames) && settings.frames>0 ? `${(settings.frames/16).toFixed(2)}초` : "계산 불가"} · 가속 사용 시 4스텝과 CFG 1. 제한된 GPU 시험을 완료했으며 출력 품질은 입력과 설정에 따라 달라집니다.</p>
      <ActionButton type="submit" reasons={inputReasons}>생성 요청 검토</ActionButton>
    </fieldset></form></GeneratorSectionCard>
    {pending && <section className="fun-request-review" aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/><p>{isImage && file?.name} · 832×480 · {pending.frames}프레임 · {pending.steps}스텝 · 시드 {pending.seed} · CFG {pending.guidance_scale} · Shift {pending.flow_shift}</p><p>가속 LoRA: {pending.acceleration ? "사용" : "사용 안 함"} · {isImage ? pending.action_variant : "KXSR"} LoRA: {pending.action_lora ? `사용 (강도 ${pending.action_strength})` : "사용 안 함"}</p><p>{pending.prompt}</p><p>부정 프롬프트: {pending.negative_prompt || "없음"}</p><GenerationReviewActions busy={busy} onCancel={()=>setPending(null)} onConfirm={submit}/></section>}
    <ActiveGeneratorProgress service={service} revision={revision+":"+job} onOpenResult={setJob}/>
    <GeneratorHistory allowPriority toggleResult key={revision} service={service} statusCommand="status" card openResult={setJob} resultId={job} onCloseResult={()=>setJob("")} onSelectedDeleted={(id,message)=>{if(job===id)setJob("");setNotice(message);setRevision(x=>x+1);}} footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={message=>{setJob("");setNotice(message);setRevision(x=>x+1);}}/>} renderResult={(id)=><section><SavedGeneratorInputs id={id} service={service} statusCommand="status"/><MediaJobResult service={service} id={id}>{(record,reload)=>record && <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>}</MediaJobResult></section>}/>
  </article>;
}
export function Wan21T2VPage(props){return <Wan21VideoPage {...props} mode="t2v"/>;}
export function Wan21I2VPage(props){return <Wan21VideoPage {...props} mode="i2v"/>;}
