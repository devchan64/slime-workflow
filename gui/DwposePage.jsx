import {generationReady} from "./generationReady.mjs";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import useGpuHandoff from "./useGpuHandoff.js";
import ActionButton from "./ActionButton.jsx";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import GeneratorJobResult from "./GeneratorJobResult.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import React, {useEffect,useId,useRef,useState} from "react";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorSectionNavigation,{openGeneratorHistory} from "./GeneratorSectionNavigation.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";

async function pngData(file) {
  const signature=new Uint8Array(await file.slice(0,8).arrayBuffer());
  if(signature.join(",")!=="137,80,78,71,13,10,26,10")throw new Error("PNG 파일을 선택하세요.");
  const image=await createImageBitmap(file);
  const valid=image.width===832 && image.height===480;
  image.close();
  if(!valid)throw new Error("832×480 PNG가 필요합니다.");
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(reader.result.split(",")[1]);
    reader.onerror=()=>reject(new Error("파일을 읽을 수 없습니다."));
    reader.readAsDataURL(file);
  });
}

export default function DwposePage({embedded=false,session:embeddedSession=""}={}) {
  const busyId=useId(),lockedId=useId();
  const query=new URLSearchParams(location.search);
  const session=embeddedSession || query.get("session") || "";
  const [file,setFile]=useState(null),[hands,setHands]=useState(false),[face,setFace]=useState(false);
  const inputRef=useRef({file,hands,face});inputRef.current={file,hands,face};
  const imageSelectionRevision=useRef(0),imageChecking=useRef(false);
  const [imageCheckPending,setImageCheckPending]=useState(false);
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[model,setModel]=useState(null);
  const reviewEpoch=useRef(0),interactionRef=useRef({busy,pending});interactionRef.current={busy,pending};
  const [job,setJob]=useState(embedded ? "" : query.get("job") || ""),[notice,setNotice]=useState("");
  const [historyRevision,setHistoryRevision]=useState(0);
  const formRegion=useRef(null),historyRegion=useRef(null),resultRegion=useRef(null);
  const reviewRequest=useRef(null),focusFrame=useRef(null),reviewButtonRef=useRef(null),focusOnReview=useRef(false),reviewFileName=useRef("");
  useEffect(()=>()=>{const current=reviewRequest.current;reviewRequest.current=null;current?.abort();if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);},[]);
  const handoff=useGpuHandoff(session,"dwpose",setJob,setNotice);
  const reviewRef=useRef(null),handsRef=useRef(null);
  useEffect(()=>{if(!pending || !focusOnReview.current)return;focusOnReview.current=false;const frame=requestAnimationFrame(()=>restoreLostFocus(document,reviewRef.current));return ()=>cancelAnimationFrame(frame);},[pending]);
  function closeReview(){
    const restore=reviewRef.current?.contains(document.activeElement);
    const epoch=reviewEpoch.current;
    setPending(null);
    handoff.clearReview();
    if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);
    if(restore)focusFrame.current=requestAnimationFrame(()=>{focusFrame.current=null;if(epoch===reviewEpoch.current && !reviewRequest.current)restoreLostFocus(document,reviewButtonRef.current);});
  }
  function cleaned(message){
    setJob("");setNotice(message);setHistoryRevision(value=>value+1);
  }
  const sending=useRef(false);
  async function readJob(id,{signal}={}){
    const inputAtStart=inputRef.current,imageAtStart=imageSelectionRevision.current,checkingAtStart=imageChecking.current,reviewAtStart=reviewEpoch.current,focusAtStart=document.activeElement;
    const controller=new AbortController();let timedOut=false;
    const abort=()=>controller.abort();if(signal?.aborted)controller.abort();else signal?.addEventListener("abort",abort,{once:true});
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
    const response=await untilAborted(fetch("/management/assistant/dwpose-input/"+encodeURIComponent(id),{cache:"no-store",signal:controller.signal}),controller.signal);
    if(!response.ok)throw new Error("저장된 DWPose 입력을 불러올 수 없습니다.");
    const handsHeader=response.headers.get("X-Pose-Hands"),faceHeader=response.headers.get("X-Pose-Face");
    if(!["true","false"].includes(handsHeader) || !["true","false"].includes(faceHeader))throw new Error("저장된 포즈 옵션을 확인할 수 없습니다. 이력을 다시 조회하세요.");
    const blob=await untilAborted(response.blob(),controller.signal);
    const savedFile=new File([blob],id+"-reference.png",{type:"image/png"});
    try{await untilAborted(pngData(savedFile),controller.signal);}catch(error){if(controller.signal.aborted)throw error;throw new Error("저장된 PNG를 확인할 수 없습니다. 이력을 다시 조회하세요.");}
    return {id,file:savedFile,inputAtStart,imageAtStart,checkingAtStart,reviewAtStart,focusAtStart,request:{
      pose_include_hands:handsHeader==="true",
      pose_include_face:faceHeader==="true",
    }};
    }catch(error){if(timedOut)throw new Error("저장 입력 조회 시간이 초과됐습니다. 다시 조회하세요.");throw error;}
    finally{clearTimeout(timeout);signal?.removeEventListener("abort",abort);}
  }
  function restore(request,record){
    if(record.reviewAtStart!==reviewEpoch.current || interactionRef.current.busy || interactionRef.current.pending)throw new Error("조회 중 생성 폼에서 다른 작업이 진행되어 이력 입력을 적용하지 않았습니다.");
    const current=inputRef.current,previous=record.inputAtStart;
    if(record.checkingAtStart || imageChecking.current || previous.file!==current.file || previous.hands!==current.hands || previous.face!==current.face || record.imageAtStart!==imageSelectionRevision.current)throw new Error("이미지 확인 중이거나 조회 중 입력이 변경되어 적용하지 않았습니다. 확인 후 다시 시도하세요.");
    inputRef.current={file:record.file,hands:request.pose_include_hands,face:request.pose_include_face};
    setFile(record.file);setHands(request.pose_include_hands);setFace(request.pose_include_face);
    setNotice("저장된 PNG와 포즈 옵션을 불러왔습니다.");
    if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);
    focusFrame.current=requestAnimationFrame(()=>{focusFrame.current=null;if(record.reviewAtStart===reviewEpoch.current && !reviewRequest.current && !interactionRef.current.busy && !interactionRef.current.pending && (document.activeElement===record.focusAtStart || document.activeElement===document.body) && handsRef.current?.isConnected && !handsRef.current.disabled)handsRef.current.focus();});
  }
  async function review(){
    if(imageChecking.current || reviewRequest.current)return;
    focusOnReview.current=document.activeElement===reviewButtonRef.current;
    const inputAtStart=inputRef.current,imageAtStart=imageSelectionRevision.current;
    if(!inputAtStart.file){setNotice("입력 PNG를 선택한 뒤 검토하세요.");return;}
    const inputChanged=()=>{const current=inputRef.current;return imageChecking.current || imageAtStart!==imageSelectionRevision.current || current.file!==inputAtStart.file || current.hands!==inputAtStart.hands || current.face!==inputAtStart.face;};
    const controller=new AbortController();reviewRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    reviewEpoch.current++;
    setBusy(true);setNotice("");
    try {
      const request={action:"generate",images:[await untilAborted(pngData(inputAtStart.file),controller.signal)],pose_include_hands:inputAtStart.hands,pose_include_face:inputAtStart.face};
      if(inputChanged())throw new Error("확인 중 입력이 변경되었습니다. 다시 검토하세요.");
      await untilAborted(handoff.preview(request,{signal:controller.signal}),controller.signal);
      if(reviewRequest.current===controller && !controller.signal.aborted){if(inputChanged()){handoff.clearReview();throw new Error("확인 중 입력이 변경되었습니다. 다시 검토하세요.");}reviewFileName.current=inputAtStart.file.name;setPending(request);}
    }catch(problem){if(reviewRequest.current===controller && (!controller.signal.aborted || timedOut))setNotice(timedOut ? "생성 요청 확인 시간이 초과됐습니다. 다시 시도하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timeout);if(reviewRequest.current===controller){reviewRequest.current=null;setBusy(false);}}
  }
  async function submit(){
    if(!pending || sending.current || !generationReady(model))return;
    sending.current=true;setBusy(true);
    try {
      if(handoff.review){await handoff.approve(pending);setNotice("확인한 GPU 양도 요청을 접수했습니다.");return;}
      const result=await managementCommand("dwpose","generate",pending);
      if(!result.id)throw new Error("작업 ID를 확인할 수 없습니다.");
      setJob(result.id);setNotice("공용 GPU 대기열에 등록했습니다.");
    }catch(problem){setNotice(problem.message+" · 이력에서 접수 여부를 확인하세요.");}
    finally{setPending(null);handoff.clearReview();sending.current=false;setBusy(false);}
  }
  return <article className={embedded ? "dwpose-page generator-page-common" : "dwpose-page dwpose-standalone generator-page-common"}>
    <GeneratorPageIdentity service="dwpose" embedded={embedded} showReturn returnHref={"/management/assistant/"+(session?"?"+new URLSearchParams({session}):"")} returnLabel="헤르메스 대화"/>
    <GeneratorSectionNavigation inputRef={formRegion} historyRef={historyRegion} resultRef={resultRegion} resultReady={Boolean(job)} openOnNavigate/>
    <ModelReadiness session={session} service="dwpose" onStatus={setModel}/>
    {handoff.id && <GpuHandoffStatus session={session} id={handoff.id} service="dwpose" status={handoff.status} onUpdate={handoff.update} onClose={handoff.close}/>}
    {busy && <p id={busyId} role="status">포즈 추출 요청을 처리하고 있습니다. 완료될 때까지 기다리세요.</p>}
    {!busy && (pending || handoff.id) && <p id={lockedId}>{pending ? "아래 검토를 확인하거나 입력 수정을 선택하세요." : "GPU 양도 상태를 확인하고 닫은 뒤 입력을 수정하세요."}</p>}
    <fieldset disabled={busy || Boolean(pending) || Boolean(handoff.id)} aria-describedby={busy ? busyId : pending || handoff.id ? lockedId : undefined}>
      <div ref={formRegion} tabIndex={-1} aria-label="DWPose 생성 입력">
      <ReferenceImageInput label="입력 PNG · 832×480" accept="image/png" source={file} validate={pngData} disabled={busy || Boolean(pending) || Boolean(handoff.id)} onSelectionStart={()=>{imageSelectionRevision.current++;}} onCheckingChange={value=>{imageChecking.current=value;setImageCheckPending(value);}} onChange={value=>{inputRef.current={...inputRef.current,file:value};setFile(value);}}/>
      <div className="dwpose-options"><label><input ref={handsRef} type="checkbox" checked={hands} onChange={event=>{const value=event.target.checked;inputRef.current={...inputRef.current,hands:value};setHands(value);}}/>손 상세 표시</label>
      <label><input type="checkbox" checked={face} onChange={event=>{const value=event.target.checked;inputRef.current={...inputRef.current,face:value};setFace(value);}}/>얼굴 상세 표시</label></div>
      <ActionButton buttonRef={reviewButtonRef} reasons={[imageCheckPending && "선택한 이미지 확인이 끝날 때까지 기다리세요.",!file && "입력 PNG를 선택하세요.",!generationReady(model) && "모델 준비 상태를 확인하세요."]} onClick={review}>생성 요청 검토</ActionButton>
      </div>
      <div ref={historyRegion} aria-label="DWPose 생성 이력"><GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id) cleaned(message); else setNotice(message);}} key={historyRevision} service="dwpose" readJobWithSignal={readJob} resultId={job} openResult={setJob} onCloseResult={()=>setJob("")} restore={restore} renderResult={(id,close)=><section ref={resultRegion} tabIndex={-1} aria-label="선택한 DWPose 작업 결과"><button type="button" onClick={close}>결과 닫기</button><GeneratorJobResult selectionControls job={id} service="dwpose" readJob={readJob} controls={false} onDeleted={cleaned}/></section>}/></div>
    </fieldset>
    {pending && <section ref={reviewRef} tabIndex={-1} aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><p className="reference-image-name">입력 PNG · {reviewFileName.current}</p><p>손 상세 {pending.pose_include_hands?"포함":"제외"} · 얼굴 상세 {pending.pose_include_face?"포함":"제외"}</p><GpuQueueSummary/>
      {handoff.review && <p>동의하면 진행 중인 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 포즈를 추출합니다. 작업이 끝나면 Qwen 3.8을 다시 GPU에 적재합니다.</p>}
      <GenerationReviewActions busy={busy} onCancel={closeReview} onConfirm={submit} confirmLabel={handoff.review ? "해제·생성·재적재에 동의" : undefined} disabledReason={!generationReady(model) ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : ""}/>
    </section>}
    {notice && <p role="status">{notice}</p>}
    <ActiveGeneratorProgress service="dwpose" revision={historyRevision+":"+job} onOpenResult={id=>openGeneratorHistory(historyRegion,id,setJob)}/>
    <GeneratorJobResult selectionControls job="" service="dwpose" onDeleted={cleaned}/>
  </article>;
}
