import {generationReady} from "./generationReady.mjs";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import useGpuHandoff from "./useGpuHandoff.js";
import ActionButton from "./ActionButton.jsx";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import GeneratorJobResult from "./GeneratorJobResult.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import React, {useEffect,useRef,useState} from "react";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import {managementCommand} from "./managementCommand.js";

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
  const query=new URLSearchParams(location.search);
  const session=embeddedSession || query.get("session") || "";
  const [file,setFile]=useState(null),[hands,setHands]=useState(false),[face,setFace]=useState(false);
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[model,setModel]=useState(null);
  const [job,setJob]=useState(embedded ? "" : query.get("job") || ""),[notice,setNotice]=useState("");
  const [historyRevision,setHistoryRevision]=useState(0);
  const handoff=useGpuHandoff(session,"dwpose",setJob,setNotice);
  const reviewRef=useRef(null),handsRef=useRef(null);
  useEffect(()=>{if(pending)reviewRef.current?.focus();},[pending]);
  function closeReview(){
    setPending(null);
    handoff.clearReview();
    requestAnimationFrame(()=>handsRef.current?.focus());
  }
  function cleaned(message){
    setJob("");setNotice(message);setHistoryRevision(value=>value+1);
  }
  const sending=useRef(false);
  async function readJob(id){
    const response=await fetch("/management/assistant/dwpose-input/"+encodeURIComponent(id),{cache:"no-store"});
    if(!response.ok)throw new Error("저장된 DWPose 입력을 불러올 수 없습니다.");
    const blob=await response.blob();
    const savedFile=new File([blob],id+"-reference.png",{type:"image/png"});
    return {id,file:savedFile,request:{
      pose_include_hands:response.headers.get("X-Pose-Hands")==="true",
      pose_include_face:response.headers.get("X-Pose-Face")==="true",
    }};
  }
  function restore(request,record){
    setFile(record.file);setHands(request.pose_include_hands);setFace(request.pose_include_face);
    setJob(record.id);setNotice("저장된 PNG와 포즈 옵션을 불러왔습니다.");
  }
  async function review(){
    setBusy(true);setNotice("");
    try {
      const request={action:"generate",images:[await pngData(file)],pose_include_hands:hands,pose_include_face:face};
      await handoff.preview(request);setPending(request);
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
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
    <ModelReadiness service="dwpose" onStatus={setModel}/>
    {handoff.id && <GpuHandoffStatus session={session} id={handoff.id} service="dwpose" status={handoff.status} onUpdate={handoff.update} onClose={handoff.close}/>}
    <fieldset disabled={busy || Boolean(pending) || Boolean(handoff.id)}>
      <ReferenceImageInput label="입력 PNG · 832×480" accept="image/png" source={file} validate={pngData} disabled={busy || Boolean(pending)} onChange={setFile}/>
      {file && <p>선택된 입력 · {file.name}</p>}
      <GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id) cleaned(message); else setNotice(message);}} key={historyRevision} service="dwpose" readJob={readJob} externalResultId={job} restore={restore} inspectResult={record=>setJob(record.id)}/>
      <div className="dwpose-options"><label><input ref={handsRef} type="checkbox" checked={hands} onChange={event=>setHands(event.target.checked)}/>손 상세 표시</label>
      <label><input type="checkbox" checked={face} onChange={event=>setFace(event.target.checked)}/>얼굴 상세 표시</label></div>
      <ActionButton reasons={[!file && "입력 PNG를 선택하세요.",!generationReady(model) && "모델 준비 상태를 확인하세요."]} onClick={review}>생성 요청 검토</ActionButton>
    </fieldset>
    {pending && <section ref={reviewRef} tabIndex={-1} aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><p>입력 PNG · {file.name}</p><p>손 상세 {pending.pose_include_hands?"포함":"제외"} · 얼굴 상세 {pending.pose_include_face?"포함":"제외"}</p><GpuQueueSummary/>
      {handoff.review && <p>동의하면 진행 중인 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 포즈를 추출합니다. 작업이 끝나면 Qwen 3.8을 다시 GPU에 적재합니다.</p>}
      <GenerationReviewActions busy={busy} onCancel={closeReview} onConfirm={submit} confirmLabel={handoff.review ? "해제·생성·재적재에 동의" : undefined} disabledReason={!generationReady(model) ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : ""}/>
    </section>}
    {notice && <p role="status">{notice}</p>}
    <GeneratorJobResult selectionControls job={job} service="dwpose" controls={false} onDeleted={cleaned}/>
  </article>;
}
