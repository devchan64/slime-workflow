import PromptWordCount from "./PromptWordCount.jsx";
import SeedInput from "./SeedInput.jsx";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import React,{useEffect,useRef,useState} from "react";
import {referencePng,videoData} from "./videoInputs.js";
import {managementCommand} from "./managementCommand.js";
import {generationReady} from "./generationReady.mjs";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import useGpuHandoff from "./useGpuHandoff.js";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";

export default function AnimateInputs({saved,onSelectionStart,onJob,session,model,loraModel,onInteractionChange}) {
  const [prompt,setPrompt]=useState(saved?.request.prompt ?? "");
  const [seed,setSeed]=useState(saved?.request.seed ?? "42");
  const [reference,setReference]=useState(saved?.reference ?? null);
  const [motionError,setMotionError]=useState(false);
  const [motionFile,setMotionFile]=useState(null);
  const motionInput=useRef(null);
  const [frames,setFrames]=useState(saved?.request.frames ?? 21);
  const [steps,setSteps]=useState(saved?.request.steps ?? 40);
  const [lora,setLora]=useState(saved?.request.lora_mode ?? "none");
  const [busy,setBusy]=useState(false),[pending,setPending]=useState(null),[error,setError]=useState("");
  const sending=useRef(false);
  const handoff=useGpuHandoff(session,"wan22-animate2",onJob,setError);
  useEffect(()=>{onInteractionChange?.(busy || Boolean(pending));},[busy,pending,onInteractionChange]);
  useEffect(()=>{setPrompt(saved?.request.prompt ?? "");setSeed(saved?.request.seed ?? "42");setReference(saved?.reference ?? null);setFrames(saved?.request.frames ?? 21);setSteps(saved?.request.steps ?? 40);setLora(saved?.request.lora_mode ?? "none");setMotionError(false);setMotionFile(null);if(motionInput.current)motionInput.current.value="";},[saved]);
  async function materialize(value,type){
    if(typeof value!=="string")return value;
    const response=await fetch(value,{cache:"no-store"});
    if(!response.ok)throw new Error("저장된 입력 파일을 읽을 수 없습니다.");
    return new File([await response.blob()],type==="image/png" ? "reference.png" : "motion.mp4",{type});
  }
  async function review(event){
    event.preventDefault();if(busy || pending)return;
    setBusy(true);setError("");
    try{
      if(!reference || !(motionFile || saved?.motion))throw new Error("참조 이미지와 동작 영상을 선택하세요.");
      const numeric=[Number(frames),Number(steps),Number(seed)];
      if(!numeric.every(Number.isInteger) || numeric[0]<5 || numeric[0]>81 || (numeric[0]-1)%4 || numeric[1]<2 || numeric[1]>50 || numeric[2]<0 || numeric[2]>2147483647 || String(seed).trim()==="")throw new Error("프레임, 스텝과 시드 범위를 확인하세요.");
      if(!prompt.trim())throw new Error("캐릭터 외형·배경 설명을 입력하세요.");
      const image=await materialize(reference,"image/png"), motion=await materialize(motionFile || saved.motion,"video/mp4");
      const request={action:"generate",images:[await referencePng(image)],driving_video:await videoData(motion),prompt,frames:numeric[0],steps:numeric[1],seed:numeric[2],width:832,height:480,lora_mode:lora};
      await handoff.preview(request);setPending(request);
    }catch(problem){setError(problem.message || "입력을 확인할 수 없습니다.");}
    finally{setBusy(false);}
  }
  async function submit(){
    if(!pending || sending.current || !generationReady(model) || (pending.lora_mode==='lightx2v' && !loraModel?.ready))return;
    sending.current=true;setBusy(true);setError("");
    try{
      if(handoff.review)await handoff.approve(pending);
      else {const result=await managementCommand("wan22-animate2","generate",pending);if(!result.id)throw new Error("접수 ID를 확인할 수 없습니다.");onJob(result.id);}
      setPending(null);handoff.clearReview();
    }catch(problem){setError((problem.message || "접수 실패")+" · 재접수 전에 생성 이력을 확인하세요.");setPending(null);handoff.clearReview();}
    finally{sending.current=false;setBusy(false);}
  }
  return (
    <><form onSubmit={review}><fieldset className="animate-inputs" disabled={busy || Boolean(pending)}><legend>캐릭터 동작 전사 입력</legend>
      {saved && <section><p>복원한 작업</p><JobIdentifier id={saved.id} compact/><video key={saved.motion} aria-label="저장된 동작 영상" controls preload="metadata" src={saved.motion} onError={()=>setMotionError(true)}/>
        {motionError && <p role="status">이 브라우저에서 저장된 동작 영상을 재생할 수 없습니다. 원본 파일을 열어 확인하세요.</p>}
        <a href={saved.motion} target="_blank" rel="noreferrer">동작 영상 원본 열기</a></section>}
      <ReferenceImageInput label="캐릭터 참조 PNG · 832×480" source={reference} onSelectionStart={onSelectionStart} onChange={value=>{onSelectionStart?.();setReference(value);}} accept="image/png"/>
      <div className="animate-motion-file"><span>RGB 동작 MP4 · 16fps 샘플링</span><label className="reference-image-file">영상 파일 선택<input ref={motionInput} aria-label="RGB 동작 MP4 · 16fps 샘플링" type="file" accept="video/mp4" onChange={event=>setMotionFile(event.target.files[0] || null)}/></label>{motionFile && <small>선택한 파일 · {motionFile.name}</small>}</div>
      <label>캐릭터 외형·배경 설명<textarea maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <p><PromptWordCount text={prompt} final/> · 원문 그대로 전달</p>
      <label>프레임<input type="number" min={5} max={81} step={4} value={frames} onChange={event=>setFrames(event.target.value)}/></label>
      <label>가속 LoRA<select value={lora} onChange={event=>{const value=event.target.value;setLora(value);setSteps(value==='lightx2v' ? 6 : 40);}}><option value="none">사용 안 함 · Base</option><option value="lightx2v">LightX2V · 6스텝</option></select></label>
      <label>스텝<input type="number" min={2} max={50} value={steps} onChange={event=>setSteps(event.target.value)}/></label>
      <SeedInput value={seed} max={2147483647} onChange={setSeed} required={false}/>
      <p>{lora === 'lightx2v' ? 'LightX2V 강도 1 · LCM · shift 5 · CFG 1 · 생성 품질 검증 필요' : '공식 Base BF16 · 공식 스케줄러 및 CFG'} · AMD ROCm GPU 연산</p>
      <button type="submit">생성 요청 검토</button>
    </fieldset></form>
    {pending && <section aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/><p>{pending.frames}프레임 · 16fps · {pending.steps}스텝 · 시드 {pending.seed} · {pending.lora_mode==='lightx2v' ? 'LightX2V 강도 1 · CFG 1 · shift 5 · LCM' : 'Base'}</p><p>{pending.prompt}</p>{handoff.review && <p>동의하면 진행 중인 대화가 끝난 뒤 대화 모델을 해제하고, 생성 후 다시 적재합니다.</p>}<GenerationReviewActions busy={busy} onCancel={()=>{setPending(null);handoff.clearReview();}} onConfirm={submit} confirmLabel={handoff.review ? '해제·생성·재적재에 동의' : undefined} disabledReason={!generationReady(model) ? '기본 모델 준비 상태를 확인하세요.' : pending.lora_mode==='lightx2v' && !loraModel?.ready ? 'LightX2V LoRA를 먼저 준비하세요.' : ''}/></section>}
    {error && <p role="alert">{error}</p>}
    {handoff.id && <GpuHandoffStatus session={session} id={handoff.id} service="wan22-animate2" status={handoff.status} onUpdate={handoff.update} onClose={handoff.close}/>}</>
  );
}
