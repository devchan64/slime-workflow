import PromptWordCount from "./PromptWordCount.jsx";
import SeedInput from "./SeedInput.jsx";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import React,{useEffect,useId,useRef,useState} from "react";
import {referencePng,videoData} from "./videoInputs.js";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {generationReady} from "./generationReady.mjs";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ReviewPrompt from "./ReviewPrompt.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import useGpuHandoff from "./useGpuHandoff.js";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import ActionButton from "./ActionButton.jsx";
import InputVideoPreview from "./InputVideoPreview.jsx";
import {validAnimateVideoInfo} from "./videoFrameLimit.mjs";
import {prepareAnimatePreview} from "./animatePreview.mjs";

export default function AnimateInputs({saved,onSelectionStart,onJob,session,model,loraModel,onInteractionChange,onAttachmentCheckingChange}) {
  const videoHelpId=useId(),videoErrorId=useId(),frameErrorId=useId(),stepErrorId=useId(),inputLockId=useId();
  const [prompt,setPrompt]=useState(saved?.request.prompt ?? "");
  const [seed,setSeed]=useState(saved?.request.seed ?? "42");
  const [reference,setReference]=useState(saved?.reference ?? null);
  const [motionError,setMotionError]=useState(false);
  const [motionFile,setMotionFile]=useState(null);
  const [videoInfo,setVideoInfo]=useState(null),[videoError,setVideoError]=useState(""),[checkingVideo,setCheckingVideo]=useState(false);
  const [videoRevision,retryVideo]=useState(0);
  const [imageCheckPending,setImageCheckPending]=useState(false),imageChecking=useRef(false),videoChecking=useRef(false);
  const checkingCallback=useRef(onAttachmentCheckingChange);checkingCallback.current=onAttachmentCheckingChange;
  function updateVideoChecking(value){videoChecking.current=value;setCheckingVideo(value);checkingCallback.current?.(value || imageChecking.current);}
  const motionInput=useRef(null),videoRetryFocus=useRef(false),videoInfoRef=useRef(null);
  const formRef=useRef(null),reviewRef=useRef(null),reviewOrigin=useRef(null);
  const reviewRequest=useRef(null);
  const currentReviewScope=useRef({session,saved}),previousReviewScope=useRef({session,saved}),pendingScope=useRef(null);
  currentReviewScope.current={session,saved};
  const sameScope=(left,right)=>Boolean(left && right && left.session===right.session && left.saved===right.saved);
  useEffect(()=>()=>{const current=reviewRequest.current;reviewRequest.current=null;current?.abort();},[]);
  const [frames,setFrames]=useState(saved?.request.frames ?? 21);
  const [steps,setSteps]=useState(saved?.request.steps ?? 40);
  const [lora,setLora]=useState(saved?.request.lora_mode ?? "none");
  const [busy,setBusy]=useState(false),[pending,setPending]=useState(null),[error,setError]=useState("");
  const sending=useRef(false);
  const handoff=useGpuHandoff(session,"wan22-animate2",onJob,setError);
  useEffect(()=>{
    const current={session,saved};
    if(sameScope(previousReviewScope.current,current))return;
    previousReviewScope.current=current;
    const request=reviewRequest.current;
    if(request){reviewRequest.current=null;request.abort();setBusy(false);}
    pendingScope.current=null;setPending(null);handoff.clearReview();setError("");
  },[session,saved]);
  useEffect(()=>{onInteractionChange?.(busy || Boolean(pending));},[busy,pending,onInteractionChange]);
  useEffect(()=>{setPrompt(saved?.request.prompt ?? "");setSeed(saved?.request.seed ?? "42");setReference(saved?.reference ?? null);setFrames(saved?.request.frames ?? 21);setSteps(saved?.request.steps ?? 40);setLora(saved?.request.lora_mode ?? "none");setMotionError(false);setMotionFile(null);if(motionInput.current)motionInput.current.value="";},[saved]);
  useEffect(()=>{
    const source=motionFile || saved?.motion;
    setVideoInfo(null);setVideoError("");
    if(!source){updateVideoChecking(false);return;}
    const controller=new AbortController();let active=true,timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    updateVideoChecking(true);
    (async()=>{try{
      let file=source;
      if(typeof source==='string'){
        const response=await untilAborted(fetch(source,{cache:'no-store',signal:controller.signal}),controller.signal);
        if(!response.ok)throw new Error('저장된 동작 영상을 읽을 수 없습니다.');
        file=await untilAborted(response.blob(),controller.signal);
      }
      if(file.size>32*1024*1024)throw new Error('MP4는 32MiB 이하여야 합니다.');
      const response=await untilAborted(fetch('/management/assistant/animate-video-info',{method:'POST',body:file,signal:controller.signal}),controller.signal);
      const info=await untilAborted(response.json(),controller.signal);
      if(!response.ok || !validAnimateVideoInfo(info))throw new Error(info?.error || '영상 정보를 확인할 수 없습니다.');
      if(active)setVideoInfo(info);
    }catch(problem){if(active)setVideoError(timedOut ? '영상 확인 시간이 초과됐습니다. 다시 선택하세요.' : problem.message || '영상을 확인할 수 없습니다.');}
    finally{clearTimeout(timer);if(active)updateVideoChecking(false);}})();
    return ()=>{active=false;clearTimeout(timer);controller.abort();};
  },[motionFile,saved,videoRevision]);
  useEffect(()=>{if(!checkingVideo && videoRetryFocus.current){videoRetryFocus.current=false;requestAnimationFrame(()=>{if(document.activeElement===document.body)videoInfoRef.current?.focus();});}},[checkingVideo]);
  const frameNumber=Number(frames),stepNumber=Number(steps),seedNumber=Number(seed);
  const invalidFrames=frames==='' || !Number.isInteger(frameNumber) || frameNumber<5 || frameNumber>81 || (frameNumber-1)%4!==0;
  const exceedsVideo=Boolean(videoInfo && frameNumber>videoInfo.maximum_frames);
  const invalidSteps=steps===''  || !Number.isInteger(stepNumber) || stepNumber<2 || stepNumber>50;
  const invalidSeed=String(seed).trim()==='' || !Number.isInteger(seedNumber) || seedNumber<0 || seedNumber>2147483647;
  const reviewReasons=[imageCheckPending && '참조 이미지 확인이 끝날 때까지 기다리세요.',!reference && '참조 PNG를 선택하세요.',!(motionFile || saved?.motion) && '동작 MP4를 선택하세요.',checkingVideo && '동작 영상 정보를 확인하고 있습니다.',videoError,exceedsVideo && `입력 영상은 최대 ${videoInfo.maximum_frames}프레임까지 지원합니다.`,!prompt.trim() && '캐릭터 외형·배경 설명을 입력하세요.',invalidFrames && '프레임은 5~81의 4n+1이어야 합니다.',invalidSteps && '스텝은 2~50이어야 합니다.',invalidSeed && '시드를 확인하세요.',!generationReady(model) && '기본 모델 준비 상태를 확인하세요.',lora==='lightx2v' && !loraModel?.ready && 'LightX2V LoRA를 준비하세요.'];
  async function materialize(value,type,signal){
    if(typeof value!=="string")return value;
    const response=await fetch(value,{cache:"no-store",signal});
    if(!response.ok)throw new Error("저장된 입력 파일을 읽을 수 없습니다.");
    return new File([await response.blob()],type==="image/png" ? "reference.png" : "motion.mp4",{type});
  }
  async function review(event){
    event.preventDefault();if(busy || pending || imageChecking.current || videoChecking.current || reviewReasons.some(Boolean))return;
    if(reviewRequest.current)return;
    const controller=new AbortController();reviewRequest.current=controller;let timedOut=false;
    const requestScope=currentReviewScope.current;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    reviewOrigin.current=document.activeElement;
    setBusy(true);setError("");
    try{
      if(!reference || !(motionFile || saved?.motion))throw new Error("참조 이미지와 동작 영상을 선택하세요.");
      const numeric=[Number(frames),Number(steps),Number(seed)];
      if(!numeric.every(Number.isInteger) || numeric[0]<5 || numeric[0]>81 || (numeric[0]-1)%4 || numeric[1]<2 || numeric[1]>50 || numeric[2]<0 || numeric[2]>2147483647 || String(seed).trim()==="")throw new Error("프레임, 스텝과 시드 범위를 확인하세요.");
      if(!prompt.trim())throw new Error("캐릭터 외형·배경 설명을 입력하세요.");
      const request=await untilAborted(prepareAnimatePreview({reference,motion:motionFile || saved.motion,prompt,frames:numeric[0],steps:numeric[1],seed:numeric[2],lora,
        signal:controller.signal,materialize,referencePng,videoData,previewHandoff:handoff.preview}),controller.signal);
      if(reviewRequest.current===controller && sameScope(requestScope,currentReviewScope.current)){pendingScope.current=requestScope;setPending(request);}
    }catch(problem){if(reviewRequest.current===controller && sameScope(requestScope,currentReviewScope.current))setError(timedOut ? "입력 검토 시간이 초과됐습니다. 입력을 확인한 뒤 다시 시도하세요." : problem.message || "입력을 확인할 수 없습니다.");}
    finally{clearTimeout(timeout);if(reviewRequest.current===controller){reviewRequest.current=null;setBusy(false);}}
  }
  useEffect(()=>{if(!pending)return;const origin=reviewOrigin.current;requestAnimationFrame(()=>{if((document.activeElement===document.body || document.activeElement===origin) && reviewRef.current?.isConnected)reviewRef.current.focus();});},[pending]);
  async function submit(){
    if(!pending || !sameScope(pendingScope.current,currentReviewScope.current) || sending.current || !generationReady(model) || (pending.lora_mode==='lightx2v' && !loraModel?.ready))return;
    sending.current=true;setBusy(true);setError("");
    try{
      if(handoff.review)await handoff.approve(pending);
      else {const result=await managementCommand("wan22-animate2","generate",pending);if(!result.id)throw new Error("접수 ID를 확인할 수 없습니다.");onJob(result.id);}
      setPending(null);handoff.clearReview();
    }catch(problem){setError((problem.message || "접수 실패")+" · 재접수 전에 생성 이력을 확인하세요.");setPending(null);handoff.clearReview();}
    finally{sending.current=false;setBusy(false);}
  }
  return (
    <><form ref={formRef} tabIndex={-1} aria-label="캐릭터 동작 전사 입력" onSubmit={review}><fieldset className="animate-inputs" disabled={busy || Boolean(pending)} aria-describedby={busy || pending ? inputLockId : undefined}><legend className="generator-visually-hidden">캐릭터 동작 전사 입력</legend>
      <div className="generator-input-group"><h2>입력 자료</h2><p className="generator-group-help">움직일 캐릭터와 동작의 원본 영상을 선택하세요.</p>
      {saved && <div className="generator-source-job"><span>불러온 원본 작업</span> <JobIdentifier id={saved.id} compact/></div>}
      <div className="generator-attachments">
      <ReferenceImageInput label="캐릭터 참조 PNG · 필수 · 832×480" source={reference} disabled={busy || Boolean(pending)} onSelectionStart={onSelectionStart} onCheckingChange={value=>{imageChecking.current=value;setImageCheckPending(value);checkingCallback.current?.(value || videoChecking.current);}} onChange={value=>{onSelectionStart?.();setReference(value);}} accept="image/png" maxBytes={8*1024*1024}/>
      <div className="generator-video-input"><span>동작 영상 · 필수</span><small id={videoHelpId}>MP4 · 최대 32MiB · 16fps로 샘플링</small>
        {saved && !motionFile && <div><video key={saved.motion} aria-label="저장된 동작 영상" controls preload="metadata" hidden={motionError} src={saved.motion} onError={()=>setMotionError(true)}/>
          {motionError && <p role="status">이 브라우저에서 저장된 동작 영상을 재생할 수 없습니다. 원본 파일을 열어 확인하세요.</p>}
          <a href={saved.motion} target="_blank" rel="noreferrer">동작 영상 원본 열기</a></div>}
        <InputVideoPreview file={motionFile} label="동작 영상"/>
        <label className="reference-image-file">영상 파일 선택<input ref={motionInput} aria-label="RGB 동작 MP4 · 16fps 샘플링" aria-invalid={videoError ? true : undefined} aria-describedby={[videoHelpId,videoError ? videoErrorId : null].filter(Boolean).join(" ")} type="file" accept="video/mp4" onChange={event=>{const file=event.target.files[0];event.target.value="";if(!file)return;onSelectionStart?.();setVideoInfo(null);updateVideoChecking(true);setMotionFile(file);}}/></label>{motionFile && <small className="reference-image-name">선택한 파일 · {motionFile.name}</small>}
        {checkingVideo && <p role="status">영상 정보를 확인하고 있습니다.</p>}{videoError && <div ref={videoInfoRef} tabIndex={-1}><p id={videoErrorId} role="alert">{videoError}</p><button type="button" disabled={checkingVideo} onClick={()=>{if(videoChecking.current)return;videoRetryFocus.current=true;updateVideoChecking(true);retryVideo(value=>value+1);}}>영상 정보 다시 확인</button></div>}
        {videoInfo && <p ref={videoInfoRef} tabIndex={-1}>입력 {videoInfo.width}×{videoInfo.height} · {videoInfo.fps.toFixed(2)}fps · {videoInfo.frame_count}프레임 · 출력 최대 {videoInfo.maximum_frames}프레임 <button type="button" onClick={()=>setFrames(videoInfo.maximum_frames)}>최대 프레임 적용</button></p>}
      </div></div></div>
      <div className="generator-input-group"><h2>장면 지시</h2>
      <label>캐릭터 외형·배경 설명<textarea maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <p><PromptWordCount text={prompt} final/> · 원문 그대로 전달</p>
      </div>
      <div className="generator-input-group"><h2>생성 설정</h2><p className="generator-group-help">출력 길이와 가속 방식을 선택하세요.</p><div className="generator-settings-grid">
      <div><label>프레임<input type="number" min={5} max={81} step={4} aria-invalid={invalidFrames || exceedsVideo || undefined} aria-describedby={invalidFrames || exceedsVideo ? frameErrorId : undefined} value={frames} onChange={event=>setFrames(event.target.value)}/></label>{(invalidFrames || exceedsVideo) && <small id={frameErrorId}>{invalidFrames ? "5~81 사이에서 4프레임 간격으로 입력하세요." : `입력 영상은 최대 ${videoInfo.maximum_frames}프레임까지 지원합니다.`}</small>}</div>
      <label>가속 LoRA<select value={lora} onChange={event=>{const value=event.target.value;setLora(value);setSteps(value==='lightx2v' ? 6 : 40);}}><option value="none">사용 안 함 · Base</option><option value="lightx2v">LightX2V · 6스텝</option></select></label>
      <div><label>스텝<input type="number" min={2} max={50} aria-invalid={invalidSteps || undefined} aria-describedby={invalidSteps ? stepErrorId : undefined} value={steps} onChange={event=>setSteps(event.target.value)}/></label>{invalidSteps && <small id={stepErrorId}>2~50의 정수를 입력하세요.</small>}</div>
      <SeedInput value={seed} max={2147483647} error={invalidSeed ? "0~2147483647의 정수를 입력하세요." : ""} onChange={setSeed}/>
      </div>{!invalidFrames && !exceedsVideo && <p>출력 16fps · 예상 재생 길이 {(frameNumber/16).toFixed(2)}초</p>}
      <p>{lora === 'lightx2v' ? 'LightX2V 강도 1 · LCM · shift 5 · CFG 1 · 생성 품질 검증 필요' : '공식 Base BF16 · 공식 스케줄러 및 CFG'} · AMD ROCm GPU 연산</p>
      </div>
      <ActionButton type="submit" reasons={reviewReasons}>생성 요청 검토</ActionButton>
    </fieldset>{(busy || pending) && <p id={inputLockId} role="status">{busy ? "요청을 처리하고 있습니다. 잠시 기다려 주세요." : "입력을 수정하려면 생성 요청 검토에서 입력 수정을 선택하세요."}</p>}</form>
    {pending && sameScope(pendingScope.current,currentReviewScope.current) && <section ref={reviewRef} tabIndex={-1} className="fun-request-review" aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/><p>{pending.frames}프레임 · 16fps · {pending.steps}스텝 · 시드 {pending.seed} · {pending.lora_mode==='lightx2v' ? 'LightX2V 강도 1 · CFG 1 · shift 5 · LCM' : 'Base'}</p><ReviewPrompt label="캐릭터 외형·배경 설명" text={pending.prompt}/>{handoff.review && <p>동의하면 진행 중인 대화가 끝난 뒤 대화 모델을 해제하고, 생성 후 다시 적재합니다.</p>}<GenerationReviewActions busy={busy} onCancel={()=>{const focused=document.activeElement;pendingScope.current=null;setPending(null);handoff.clearReview();requestAnimationFrame(()=>{if(document.activeElement===document.body || document.activeElement===focused)formRef.current?.focus();});}} onConfirm={submit} confirmLabel={handoff.review ? '해제·생성·재적재에 동의' : undefined} disabledReason={!generationReady(model) ? '기본 모델 준비 상태를 확인하세요.' : pending.lora_mode==='lightx2v' && !loraModel?.ready ? 'LightX2V LoRA를 먼저 준비하세요.' : ''}/></section>}
    {error && <p role="alert">{error}</p>}
    {handoff.id && <GpuHandoffStatus session={session} id={handoff.id} service="wan22-animate2" status={handoff.status} onUpdate={handoff.update} onClose={handoff.close}/>}</>
  );
}
