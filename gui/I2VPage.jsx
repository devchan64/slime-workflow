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
import {generationProposalScope,readGenerationProposal} from "./generationProposal.mjs";

const service="wan22-i2v";
const polearmPrompt="A warrior grips a long spear with both hands and faces a giant armored boss. The warrior steps forward and thrusts the spear toward the boss, then pulls it back and sweeps it sideways. Wide shot, the entire spear and both hands remain visible, continuous motion, stable background.";
export default function I2VPage({embedded=false,session:embeddedSession=""}={}){
  const session=embeddedSession || new URLSearchParams(location.search).get("session") || "";
  const [settings,setSettings]=useState({prompt:"",negative_prompt:"",frames:21,steps:4,seed:42,flow_shift:5,guidance_scale:1,lora_mode:"lightning",kungfu_strength:1});
  const [file,setFile]=useState(null),[model,setModel]=useState(null),[pending,setPending]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(""),[job,setJob]=useState(new URLSearchParams(location.search).get("job") || ""),[revision,setRevision]=useState(0),[notice,setNotice]=useState("");
  const sending=useRef(false);
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
    if(!generationReady(model) || !file || !s.prompt.trim() || !Number.isInteger(s.frames) || s.frames<5 || s.frames>129 || (s.frames-1)%4 || !Number.isInteger(s.seed) || s.seed<0 || s.seed>2147483647 || !Number.isInteger(s.steps) || s.steps<2 || s.steps>100 || !Number.isFinite(s.flow_shift) || s.flow_shift<0.1 || s.flow_shift>20 || !Number.isFinite(s.guidance_scale) || s.guidance_scale<1 || s.guidance_scale>10 || !Number.isFinite(s.kungfu_strength) || s.kungfu_strength<0 || s.kungfu_strength>2 || (s.lora_mode.includes("kungfu") && s.kungfu_strength<=0) || (s.lora_mode.includes("lightning") && (s.steps!==4 || s.guidance_scale!==1))){setError("이미지와 프롬프트, 프레임 및 생성 설정을 확인하세요.");return;}
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
    <GeneratorSectionCard title="모델 준비" summary="I2V 본체와 LoRA"><ModelReadiness service={service} modelManagementService="wan22-i2v-assets" onStatus={setModel}/></GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={revision+":"+job} onOpenResult={setJob}/>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <GeneratorSectionCard title="생성 입력" summary="첫 이미지와 동작 지시" defaultOpen><form onSubmit={review}><fieldset disabled={busy || !!pending}>
      <ReferenceImageInput label="첫 프레임 이미지" source={file} onChange={setFile} disabled={busy || !!pending}/><p>이미지는 흰 여백을 넣어 832×480으로 맞춥니다.</p>
      <label>장면·동작 프롬프트<textarea required maxLength={8000} value={settings.prompt} onChange={e=>field("prompt",e.target.value)}/><PromptWordCount text={settings.prompt} final/></label>
      <button type="button" onClick={()=>field("prompt",polearmPrompt)}>장병기 보스전 예시 입력</button><p>예시는 현재 프롬프트를 바꿉니다. 첫 이미지에 전신과 창 전체가 보이도록 구성하세요. 장병기 전용 LoRA는 아직 검증되지 않았습니다.</p>
      <label>부정 프롬프트<textarea maxLength={8000} value={settings.negative_prompt} onChange={e=>field("negative_prompt",e.target.value)}/><PromptWordCount text={settings.negative_prompt} final/></label>
      <label>LoRA<select value={settings.lora_mode} onChange={e=>setSettings(old=>({...old,lora_mode:e.target.value,...(e.target.value.includes("lightning")?{steps:4,guidance_scale:1}: {})}))}><option value="lightning">Lightning</option><option value="lightning_kungfu">Lightning + KungFu</option><option value="kungfu">KungFu</option><option value="none">사용 안 함</option></select></label>
      <div className="vace-settings-grid">{[["frames","프레임",5,129,4],["steps","스텝",2,100,1],["flow_shift","Flow shift",0.1,20,"any"],["guidance_scale","CFG",1,10,"any"],["kungfu_strength","KungFu 강도",0,2,"any"]].map(([key,label,min,max,step])=><label key={key}>{label}<input type="number" required min={min} max={max} step={step} value={settings[key]} onChange={e=>field(key,e.target.value===""?"":Number(e.target.value))}/></label>)}</div>
      <SeedInput value={settings.seed} max={2147483647} onChange={value=>field("seed",value===""?"":Number(value))}/>
      <p>16fps · Lightning은 4스텝·CFG 1 · KungFu 트리거: wugong. 동작 품질은 검수해야 합니다.</p>
      <button type="submit" disabled={!generationReady(model) || !file || !settings.prompt.trim()}>생성 요청 검토</button>{!generationReady(model) && <p>모델 준비 상태를 확인하세요.</p>}
    </fieldset></form></GeneratorSectionCard>
    {pending && <section className="fun-request-review" aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/><p>{file?.name} · {pending.frames}프레임 · {pending.steps}스텝 · 시드 {pending.seed} · {pending.lora_mode}</p><p>{pending.prompt}</p><p>부정 프롬프트: {pending.negative_prompt || "없음"}</p><GenerationReviewActions busy={busy} onCancel={()=>setPending(null)} onConfirm={submit}/></section>}
    <GeneratorHistory key={revision} service={service} statusCommand="status" card allowPriority openResult={setJob} resultId={job} onCloseResult={()=>setJob("")} onSelectedDeleted={(id,message)=>{if(job===id)setJob("");setNotice(message);setRevision(x=>x+1);}} footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={message=>{setJob("");setNotice(message);setRevision(x=>x+1);}}/>} renderResult={(id,close)=><section><button type="button" onClick={close}>결과 닫기</button><MediaJobResult service={service} id={id}>{(record,reload)=>record && <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>}</MediaJobResult></section>}/>
  </article>;
}
