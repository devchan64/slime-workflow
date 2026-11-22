import GenerationReviewActions from "./GenerationReviewActions.jsx";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import SeedInput from "./SeedInput.jsx";
import React,{useEffect,useId,useRef,useState} from "react";
import ResultTable from "./ResultTable.jsx";
import KeyframeCatalog from "./KeyframeCatalog.jsx";
import readReference from "./readReference.js";
import KimodoPromptExamples from "./KimodoPromptExamples.jsx";
import {managementCommand} from "./managementCommand.js";
import KimodoFrames from "./KimodoFrames.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import {requestErrorMessage} from "./requestError.mjs";
import {validateGpuHandoffStatus} from "./validateGpuHandoffStatus.mjs";
import {verifyKimodoProposal} from "./kimodoProposalMembership.mjs";

function decodeReferences(rows){
  return rows.map(({name,data})=>new File([Uint8Array.from(atob(data),c=>c.charCodeAt(0))],name,{type:"image/png"}));
}

export function KimodoInputSummary({inputs,references,placement,bundle,directions}){
  return <p aria-label="현재 생성 설정 요약">시드 {inputs.seed} · {inputs.frames}프레임 · 방향 {(inputs.directions || []).map(id=>directions[id]?.label || id).join(', ') || '없음'} · 고도 {inputs.camera_elevation_degrees}° · 참조 {references.length}장{references.length>0 && ' ('+references.map(file=>file.name).join(', ')+')'} · 키프레임 {placement?.placements?.length || 0}개 · 가중 골격 {bundle ? '선택됨' : '없음'} · 후처리 {inputs.post_processing ? '켜짐' : '꺼짐'} · 수평 이동 제거 {inputs.remove_horizontal_motion ? '켜짐' : '꺼짐'}</p>;
}

export function KimodoAcceptedResult({id,choose}){
  return <KimodoFrames key={id} id={id} choose={choose} selectionControls/>;
}

export default function KimodoGeneration({session,restoreJob,initialInputs=null,receiptScope="",proposalScope,choose}){
  const [directions,setDirections]=useState({});
  const [jointEdits,setJointEdits]=useState([]);
  const [referenceExamples,setReferenceExamples]=useState(null);
  const [attachmentRevision,setAttachmentRevision]=useState(0);
  const [references,setReferences]=useState([]);
  const [bundle,setBundle]=useState(null),[calibration,setCalibration]=useState(null),[hip,setHip]=useState(false);
  const [angles,setAngles]=useState("");
  const [placing,setPlacing]=useState(false),[search,setSearch]=useState("");
  const [placement,setPlacement]=useState(null);
  const [segments,setSegments]=useState("");
  const [generationMode,setGenerationMode]=useState("single");
  const modeName=useId(),segmentHelp=useId();
  const segmentTokens=segments.trim() ? segments.trim().split(/\s+/) : [];
  const segmentCounts=segmentTokens.every(value=>/^\d+$/.test(value)) ? segmentTokens.map(Number) : [];
  const segmentTotal=segmentCounts.length ? segmentCounts.reduce((sum,value)=>sum+value,0) : null;
  const segmentsValid=segmentCounts.length>=2 && segmentCounts.length<=10 && segmentCounts.every(value=>value>=16 && value<=300) && segmentTotal<=300;
  const key="kimodo-generation-receipt-"+session+(receiptScope?"-proposal-"+receiptScope:"");
  const handoffKey="kimodo-gpu-handoff-"+session+(receiptScope?"-proposal-"+receiptScope:"");
  const [inputs,setInputs]=useState(null),[review,setReview]=useState(null),[busy,setBusy]=useState(false);
  const promptSegmentCount=inputs?.prompt?.split(/\r\n|\r|\n/).filter(line=>line.trim()).length || 0;
  const [sourceJob,setSourceJob]=useState("");
  const busyRef=useRef(false);
  const [receipt,setReceipt]=useState(()=>sessionStorage.getItem(key) || ""),[notice,setNotice]=useState("");
  const [receiptState,setReceiptState]=useState(()=>sessionStorage.getItem(key) ? "checking" : "editing");
  const [jobId,setJobId]=useState("");
  const [handoffReview,setHandoffReview]=useState(null);
  const [handoffId,setHandoffId]=useState(()=>session ? sessionStorage.getItem(handoffKey) || "" : "");
  const [handoffStatus,setHandoffStatus]=useState(null);
  useEffect(()=>{
    if(!handoffId || !session)return;
    let active=true;
    managementCommand("hermes-agent","hermes-gpu-handoff-status",{session_id:session,request_id:handoffId})
      .then(result=>{if(active)setHandoffStatus(validateGpuHandoffStatus(result,session,handoffId,"kimodo"));})
      .catch(()=>{if(active)setNotice("GPU 양도 상태를 확인할 수 없습니다. 상태를 다시 확인하세요.");});
    return ()=>{active=false;};
  },[]);
  async function handoffCommand(command,fields,requestJson){
    const prefix=JSON.stringify(fields).slice(1,-1);
    const response=await fetch("/management/command",{method:"POST",headers:{"Content-Type":"application/json"},
      body:`{"service":"hermes-agent","command":${JSON.stringify(command)},"payload":{${prefix},"request":${requestJson}}}`});
    const value=await response.json();
    if(!response.ok)throw new Error(value.error || value.detail || "GPU 양도 요청을 확인할 수 없습니다.");
    return value;
  }
  async function checkReceipt(id){
    const result=await managementCommand("hermes-agent","hermes-delegation-status",{request_id:id});
    if(result.request_id!==id || result.service!=="kimodo")throw new Error("접수 기록이 일치하지 않습니다.");
    if(result.state==="accepted" && /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(result.job_id || "")){
      setJobId(result.job_id);setReceiptState("accepted");setNotice("");
    }else{setJobId("");setReceiptState("unknown");setNotice("접수 여부가 확인되지 않았습니다. 접수 상태와 생성 이력을 확인해 주세요.");}
  }
  useEffect(()=>{
    if(!receipt)return;
    let active=true;
    managementCommand("hermes-agent","hermes-delegation-status",{request_id:receipt}).then(result=>{
      if(!active)return;
      if(result.request_id===receipt && result.service==="kimodo" && result.state==="accepted" && /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(result.job_id || "")){
        setJobId(result.job_id);setReceiptState("accepted");
      }else{setReceiptState("unknown");setNotice("접수 여부가 확인되지 않았습니다. 접수 상태와 생성 이력을 확인해 주세요.");}
    }).catch(()=>{if(active){setReceiptState("unknown");setNotice("접수 상태를 불러오지 못했습니다. 접수 상태를 다시 확인해 주세요.");}});
    return ()=>{active=false;};
  },[]);
  useEffect(()=>{
    const controller=new AbortController();
    fetch(restoreJob?"/management/assistant/kimodo-input/"+encodeURIComponent(restoreJob):"/management/assistant/kimodo-generation-template",{signal:controller.signal}).then(async response=>{
      if(!response.ok)throw new Error(restoreJob?"이전 작업의 입력을 불러올 수 없습니다.":"생성 기본값을 조회할 수 없습니다.");
      const defaults=await response.json();
      if(restoreJob){
        const files=decodeReferences(defaults.references);
        const attachment=field=>defaults.attachments[field]?new File([defaults.attachments[field]],field+".json",{type:"application/json"}):null;
        let restoredPlacement=null;
        if(defaults.rows.length){
          restoredPlacement=await managementCommand("hermes-agent","hermes-kimodo-keyframe-validate",{frames:defaults.inputs.frames,keyframes:defaults.rows});
          if(restoredPlacement.sources.some(source=>defaults.hashes[source.id] && defaults.hashes[source.id]!==source.source_sha256))
            throw new Error("저장된 키프레임과 현재 원본이 다릅니다.");
        }
        if(controller.signal.aborted)return;
        setPlacement(restoredPlacement);setReferences(files);setSegments(defaults.segments.join(" "));setGenerationMode(defaults.segments.length ? "sequence" : "single");setAngles(defaults.angles.join(" "));
        setBundle(attachment("proportion_reviewed_multiview"));setCalibration(attachment("proportion_face_anchor_calibration"));
        setHip(defaults.hip);setJointEdits(JSON.parse(defaults.attachments.proportion_joint_edits || "[]"));
        setSourceJob(restoreJob);setNotice(restoreJob+" 입력을 불러왔습니다.");
      }
      if(!controller.signal.aborted){setInputs(initialInputs ? {...defaults.inputs,...Object.fromEntries(["prompt","frames","steps","seed"].filter(field=>initialInputs[field]!=null).map(field=>[field,initialInputs[field]]))} : defaults.inputs);setDirections(defaults.directions);if(initialInputs?.example_id)await applyExample(initialInputs.example_id,controller.signal);}
    }).catch(error=>{if(!controller.signal.aborted)setNotice(error.message);});
    return ()=>controller.abort();
  },[restoreJob]);
  function edit(field,value){
    setInputs(previous=>({...previous,[field]:value}));setReview(null);
  }
  async function perform(action){
    if(busyRef.current)return;
    busyRef.current=true;
    setBusy(true);setNotice("");
    try{await action();}catch(error){setNotice(requestErrorMessage(error));}finally{busyRef.current=false;setBusy(false);}
  }
  function replaceReferences(files){
    setReferences(files);setJointEdits([]);setAngles("");setBundle(null);setCalibration(null);setHip(false);setReview(null);
    setAttachmentRevision(value=>value+1);
  }
  async function loadReferences(identifier){
    const response=await fetch("/management/assistant/kimodo-reference-examples"+(identifier?"/"+encodeURIComponent(identifier):""));
    if(!response.ok)throw new Error("신체 비율 예시를 불러올 수 없습니다.");
    const data=await response.json();
    if(identifier)replaceReferences(decodeReferences(data));
    else setReferenceExamples(data);
  }
  async function applyExample(identifier,signal){
    const response=await fetch("/management/assistant/kimodo-prompt-examples/"+encodeURIComponent(identifier),{signal});
    if(!response.ok)throw new Error("동작 예시 설정을 불러올 수 없습니다.");
    const example=await response.json();
    const {keyframes,segment_frames,camera_elevation_degrees=0,...settings}=example.settings || {};
    const positions=keyframes?.length?await managementCommand("hermes-agent","hermes-kimodo-keyframe-validate",
      {frames:example.frames,keyframes}):null;
    const files=decodeReferences(example.references);
    if(signal?.aborted)return;
    setSourceJob("");
    setInputs(previous=>({...previous,...settings,prompt:example.prompt,frames:example.frames,camera_elevation_degrees}));
    setPlacement(positions);setPlacing(false);replaceReferences(files);setSegments((segment_frames || []).join(" "));setGenerationMode(segment_frames?.length ? "sequence" : "single");
    setNotice(example.label+" 설정을 적용했습니다.");
  }
  async function inspect(){
    setReview(null);setHandoffReview(null);
    if(proposalScope)await verifyKimodoProposal(managementCommand,proposalScope,proposalScope.proposal);
    const request={...inputs,frames:Number(inputs.frames),steps:Number(inputs.steps),seed:Number(inputs.seed),
      guidance_scale:Number(inputs.guidance_scale),openpose_scale_percent:Number(inputs.openpose_scale_percent)};
    delete request.segment_frames;
    if(generationMode==="sequence"){
      if(!segments.trim())throw new Error("순차 생성의 구간 프레임 수를 입력하세요.");
      if(!segmentsValid)throw new Error("구간은 2~10개, 각 16~300프레임, 합계는 최대 300프레임으로 입력하세요.");
      if(promptSegmentCount!==segmentCounts.length)throw new Error("동작 설명의 줄 수와 구간 프레임 수가 같아야 합니다.");
      request.segment_frames=segmentCounts;
      request.frames=segmentTotal;
    }
    if(jointEdits.length)request.proportion_joint_edits=jointEdits;
    if(placement){
      request.keyframes=placement.placements;
      request.keyframe_source_hashes=Object.fromEntries(placement.sources.map(source=>[source.id,source.source_sha256]));
    }
    if(references.length){
      if(references.length>8)throw new Error("참조 이미지는 최대 8장입니다.");
      if(references.some(file=>file.size>3000000))throw new Error("참조 PNG는 파일당 3 MB까지 첨부할 수 있습니다.");
      request.proportion_images=await Promise.all(references.map(readReference));
    }
    if(bundle){
      if(bundle.size>2*1024*1024)throw new Error("검수 골격 묶음은 2 MiB 이하여야 합니다.");
      request.proportion_reviewed_multiview=await bundle.text();
      if(hip)request.proportion_projected_hip=true;
      if(calibration){
        if(calibration.size>65536)throw new Error("얼굴 앵커 교정 파일은 64 KiB 이하여야 합니다.");
        request.proportion_face_anchor_calibration=await calibration.text();
      }
    }
    if(angles.trim()){
      const values=angles.trim().split(/\s+/).map(Number);
      if(values.some(value=>!Number.isFinite(value)))throw new Error("카메라 각도는 공백으로 구분한 숫자로 입력하세요.");
      request.proportion_multiview_angles=values;
    }
    const response=await fetch("/management/assistant/kimodo-generation-review?serialized=true",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify(request)});
    const result=await response.json();
    if(!response.ok)throw new Error(result.detail || "생성 입력을 확인하세요.");
    const model=await fetch("/management/assistant/model-readiness/kimodo",{cache:"no-store"});
    if(!model.ok)throw new Error("모델 상태를 확인할 수 없습니다.");
    const status=await model.json();
    if(!(status.generation_ready ?? status.ready))throw new Error(status.message || "모델 준비가 필요합니다.");
    if(session){
      const owner=await managementCommand("hermes-agent","hermes-resident-status",{session_id:session});
      if(owner.session_id!==session || !owner.resident)throw new Error("대화 모델 상태를 확인할 수 없습니다.");
      if(owner.resident_id){
        if(owner.resident.state!=="ready")throw new Error("Qwen 3.8 상주 모델 상태를 확인한 뒤 다시 검토하세요.");
        const handoff=await handoffCommand("hermes-gpu-handoff-preview",{session_id:session,resident_id:owner.resident_id},result.request_json);
        if(handoff.session_id!==session || handoff.resident_id!==owner.resident_id || !/^[a-f0-9]{64}$/.test(handoff.review_hash || ""))throw new Error("GPU 양도 검토 결과가 일치하지 않습니다.");
        setHandoffReview(handoff);
      }else if(owner.resident.state!=="not_found")throw new Error("대화 모델 상태를 확인할 수 없습니다.");
    }
    setReview(result.request_json);
  }
  async function submit(){
    if(proposalScope)await verifyKimodoProposal(managementCommand,proposalScope,proposalScope.proposal);
    const id=crypto.randomUUID().replaceAll("-","");
    sessionStorage.setItem(key,id);sessionStorage.setItem("kimodo-generation-receipt-"+session,id);setReceipt(id);setReceiptState("unknown");setJobId("");setReview(null);
    // Forward the validated JSON verbatim so integral floats keep their provenance hashes.
    const response=await fetch("/management/command",{method:"POST",headers:{"Content-Type":"application/json"},
      body:`{"service":"hermes-agent","command":"hermes-delegate-kimodo","payload":{"request_id":${JSON.stringify(id)},"request":${review}}}`});
    const result=await response.json();
    if(!response.ok || result.state!=="accepted" || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(result.job_id || ""))throw new Error("접수 여부를 확인할 수 없습니다. 접수 상태를 조회해 주세요.");
    setJobId(result.job_id);setReceiptState("accepted");setNotice("GPU 대기열에 등록했습니다.");
  }
  async function submitHandoff(){
    if(proposalScope)await verifyKimodoProposal(managementCommand,proposalScope,proposalScope.proposal);
    const id=crypto.randomUUID().replaceAll("-","");
    sessionStorage.setItem(handoffKey,id);setHandoffId(id);setHandoffStatus({state:"checking"});
    const result=await handoffCommand("hermes-gpu-handoff-approve",{request_id:id,session_id:session,
      resident_id:handoffReview.resident_id,review_hash:handoffReview.review_hash,confirmed:true},review);
    validateGpuHandoffStatus(result,session,id,"kimodo");
    if(!["approved","waiting_release","submitting","running","reload_queued","reloading","ready"].includes(result.state))throw new Error("GPU 양도 접수 여부를 확인할 수 없습니다. 상태를 확인하세요.");
    setHandoffStatus(result);setReview(null);setHandoffReview(null);
    setNotice("확인한 GPU 양도 요청을 접수했습니다. 진행 상태를 확인하세요.");
  }
  const reviewed=review ? JSON.parse(review) : null;
  return <section aria-label="Kimodo 모션 생성"><h2>모션 생성</h2>
    <details className="kimodo-generation-guide"><summary>모션 생성 사용 안내</summary>
      <ol>
        <li>모델 준비 상태를 확인합니다. 예제를 사용하려면 동작 예시에서 선택하고 <strong>예시 불러오기</strong>를 누릅니다.</li>
        <li>하나의 동작은 <strong>일반 생성</strong>, 여러 동작을 연결하려면 <strong>순차 생성</strong>을 선택합니다. 순차 생성은 동작 설명을 구간마다 한 줄씩 쓰고 구간별 프레임을 공백으로 구분합니다. 2~10구간, 각 16프레임 이상, 합계 300프레임 이하입니다.</li>
        <li>예를 들어 바닥 휴식 예제는 서서 앉기·앉아 쉬기·다시 서기의 세 구간을 <strong>64 64 64</strong>프레임으로 생성합니다. 30fps 기준 총 약 6.4초이며, 생성 단계 100은 구간마다 적용되어 총 300단계입니다.</li>
        <li>시드·출력 방향·신체 비율 참조·후처리를 확인하고 <strong>생성 요청 검토</strong>를 누릅니다. 요약을 확인한 후 <strong>확인 후 대기열에 추가</strong>를 누릅니다.</li>
        <li>완료 후 결과 영상을 재생해 시작·휴식·종료 자세와 전환을 확인합니다. DWPose 경고가 있더라도 원본 모션과 직접 포즈가 생성되면 전체 작업은 완료입니다. 원하는 동작이 아니면 시드 또는 설명을 하나씩 바꿔 비교하세요.</li>
      </ol>
      <p>GPU 메모리가 남아도 시스템 메모리 보호, 예약 또는 동시 실행 제한 때문에 대기할 수 있습니다. 접수 상태와 대기 사유를 확인하세요.</p>
    </details>
    {handoffId && <GpuHandoffStatus session={session} id={handoffId} service="kimodo" status={handoffStatus} onUpdate={setHandoffStatus}
      onClose={()=>{sessionStorage.removeItem(handoffKey);setHandoffId("");setHandoffStatus(null);}}>
      {handoffStatus?.job_id && <KimodoAcceptedResult id={handoffStatus.job_id} choose={choose}/>}
    </GpuHandoffStatus>}
    {inputs && sourceJob && <div><p>불러온 원본 작업</p><JobIdentifier id={sourceJob} compact/></div>}
    {receiptState!=="editing" && <section className="kimodo-submission-status" aria-label="생성 접수 상태">
      <h3>{receiptState==="accepted"?"생성 요청 접수됨":receiptState==="checking"?"접수 상태 확인 중":"접수 상태 확인 필요"}</h3>
      {receipt && <p>접수 ID <code>{receipt}</code></p>}
      {jobId && <KimodoAcceptedResult id={jobId} choose={choose}/>}
      <button type="button" disabled={busy || !receipt} onClick={()=>perform(()=>checkReceipt(receipt))}>접수 상태 확인</button>
      {receiptState==="accepted" && <button type="button" disabled={busy} onClick={()=>{setReceiptState("editing");setReview(null);setNotice("입력을 다시 사용합니다. 생성 요청을 확인하면 별도의 새 작업이 접수됩니다.");}}>입력 다시 사용</button>}
    </section>}
    <div hidden={receiptState!=="editing"}>
    {inputs && <fieldset disabled={busy}><legend>키프레임 배치</legend>
      <button aria-expanded={placing} onClick={()=>setPlacing(!placing)}>{placing?"배치 편집 닫기":"키프레임 배치 편집"}</button>
      {placement && <><p>{placement.placements.map(item=>item.frame+"프레임 · "+item.id).join(", ")}</p>
        <button onClick={()=>{setPlacement(null);setReview(null);setPlacing(false);}}>배치 해제</button></>}
      {placing && <><label>키프레임 검색 <input value={search} onChange={e=>setSearch(e.target.value)}/></label>
        <KeyframeCatalog query={search} initialFrames={inputs.frames} initialRows={placement?.placements || []}
          apply={(frames,result)=>{setPlacement(result);setInputs({...inputs,frames,post_processing:true,remove_horizontal_motion:false});setReview(null);setPlacing(false);}}/></>}
    </fieldset>}
    {inputs && <form onSubmit={e=>{e.preventDefault();perform(inspect);}}><fieldset disabled={busy}>
      <KimodoInputSummary inputs={inputs} references={references} placement={placement} bundle={bundle} directions={directions}/>
      <label>동작 설명 <textarea required maxLength={2000} value={inputs.prompt} aria-describedby={generationMode==="sequence" ? segmentHelp : undefined} aria-invalid={generationMode==="sequence" && segmentsValid && promptSegmentCount!==segmentCounts.length ? true : undefined} onChange={e=>edit("prompt",e.target.value)}/><PromptWordCount text={inputs.prompt}/></label>
      <KimodoPromptExamples apply={prompt=>edit("prompt",prompt)} applySettings={id=>perform(()=>applyExample(id))}/>
      <fieldset className="kimodo-mode"><legend>생성 방식</legend><div className="kimodo-mode-options">
        <label><input type="radio" name={modeName} value="single" checked={generationMode==="single"} onChange={()=>{setGenerationMode("single");setReview(null);}}/><span>일반 생성 <small>하나의 동작</small></span></label>
        <label><input type="radio" name={modeName} value="sequence" checked={generationMode==="sequence"} onChange={()=>{setGenerationMode("sequence");setReview(null);}}/><span>순차 생성 <small>여러 동작 연결</small></span></label>
      </div></fieldset>
      {generationMode==="sequence" ? <section className="kimodo-segment-settings" aria-label="순차 생성 프레임 설정">
        <label>구간별 프레임 <input type="text" inputMode="numeric" value={segments} placeholder="예: 64 32 64" aria-describedby={segmentHelp} aria-invalid={Boolean(segments.trim()) && !segmentsValid} onChange={event=>{const value=event.target.value;setSegments(value);setReview(null);const parts=value.trim().split(/\s+/);if(value.trim() && parts.length>=2 && parts.length<=10 && parts.every(part=>/^\d+$/.test(part) && Number(part)>=16 && Number(part)<=300)){const total=parts.reduce((sum,part)=>sum+Number(part),0);if(total<=300)setInputs(previous=>({...previous,frames:total}));}}}/></label>
        <p className="kimodo-segment-total">전체 프레임 <strong>{Number.isSafeInteger(segmentTotal) ? segmentTotal+"프레임" : "계산할 수 없음"}</strong>{segments.trim() && !segmentsValid && " · 아래 입력 조건을 확인하세요."}</p>
        <p id={segmentHelp}>구간별 프레임을 공백으로 구분하세요. 2~10구간, 각 16프레임 이상, 전체 300프레임 이하입니다. 동작 설명은 구간마다 한 줄씩 입력합니다. 동작 설명 {promptSegmentCount}줄 · 프레임 {segmentTokens.length}구간{segmentTokens.length>0 && promptSegmentCount!==segmentTokens.length && " · 개수를 맞춰 주세요."}</p>
      </section> : <label>프레임 수 <input type="number" required min="30" max="300" value={inputs.frames} onChange={e=>edit("frames",e.target.value)}/></label>}
      <label>생성 단계 <input type="number" required min="2" max="100" value={inputs.steps} onChange={e=>edit("steps",e.target.value)}/></label>
      <SeedInput value={inputs.seed} max={2147483647} onChange={value=>edit("seed",value)}/>
      {referenceExamples===null ? <button type="button" onClick={()=>perform(()=>loadReferences())}>신체 비율 예시 조회</button> :
        referenceExamples.map(example=><button type="button" key={example.id} onClick={()=>perform(()=>loadReferences(example.id))}>
          {example.label} 참조 적용</button>)}
      <section aria-label="신체 비율 참조 이미지"><p>신체 비율 참조 PNG · 최대 8장</p>
        <p>참조를 변경하면 참조 관절 수정과 다중 시점 설정이 초기화됩니다.</p>
        <div className="reference-image-slots">{Array.from({length:Math.min(8,references.length+1)},(_,index)=><ReferenceImageInput
          key={index} label={"신체 비율 참조 "+(index+1)} accept="image/png" maxBytes={3000000} source={references[index]} disabled={busy}
          onChange={file=>{const next=[...references];if(file)next[index]=file;else next.splice(index,1);replaceReferences(next);}}/>)}</div>
        {references.length>0 && <button type="button" onClick={()=>replaceReferences([])}>참조 전체 해제</button>}
      </section>
      {jointEdits.length>0 && <ResultTable table={{
        title:"참조 관절 수정",columns:["참조 이미지","인물","관절","원본 좌표","수정 X","수정 Y","작업"],
        rows:jointEdits.map((row,index)=>[
          references[row.image-1]?.name,row.person,row.joint,row.original.join(", "),
          ...row.edited.map((coordinate,axis)=><input type="number" required step="any"
            aria-label={row.image+"번 이미지 "+row.person+"번 인물 "+row.joint+"번 관절 "+(axis===0?"X":"Y")}
            value={coordinate} onChange={event=>{
              const value=event.target.value===""?"":Number(event.target.value);
              setJointEdits(previous=>previous.map((item,i)=>i===index?
                {...item,edited:item.edited.map((old,j)=>axis===j?value:old)}:item));
              setReview(null);
            }}/>),
          <button type="button" onClick={()=>{setJointEdits(previous=>previous.filter((_,i)=>i!==index));setReview(null);}}>수정 해제</button>
        ])
      }}/>}
      <details><summary>다중 시점 신체 비율</summary>
        <label>검출 관측 순서의 카메라 각도 8개 (도) <input value={angles} placeholder="45 0 135 90 225 315 180 270"
          onChange={e=>{setAngles(e.target.value);setReview(null);}}/></label>
        <p>참조 이미지에서 검출된 관측 순서대로 각도를 입력하세요. 각도와 검수 골격을 모두 비우면 2D 보정을 사용합니다.</p>
        <label>검수 3D 골격 묶음 JSON <input key={attachmentRevision} type="file" accept=".json,application/json"
          onChange={e=>{setBundle(e.target.files[0] || null);if(!e.target.files.length){setCalibration(null);setHip(false);}setReview(null);}}/></label>
        {bundle && <fieldset><legend>검수 골격 적용</legend>
          <label><input type="checkbox" checked={hip} onChange={e=>{setHip(e.target.checked);setReview(null);}}/>3D 투영 골반 적용</label>
          <label>얼굴 앵커 교정 JSON <input key={attachmentRevision} type="file" accept=".json,application/json"
            onChange={e=>{setCalibration(e.target.files[0] || null);setReview(null);}}/></label>
        </fieldset>}
      </details>
      <details><summary>모션 및 포즈 출력 설정</summary>
        <fieldset><legend>카메라 방향</legend>{Object.entries(directions).map(([id,direction])=>
          <label key={id}><input type="checkbox" checked={inputs.directions.includes(id)}
            onChange={e=>edit("directions",e.target.checked?[...inputs.directions,id]:inputs.directions.filter(item=>item!==id))}/>
            {direction.label} ({direction.angle}°)</label>)}</fieldset>
        <label>카메라 고도 <select value={inputs.camera_elevation_degrees} onChange={e=>edit("camera_elevation_degrees",Number(e.target.value))}>
          {[0,15,30].map(value=><option key={value} value={value}>{value}°</option>)}</select></label>
        <label>텍스트 CFG <input type="number" required min="0" max="10" step="any" value={inputs.guidance_scale}
          onChange={e=>edit("guidance_scale",e.target.value)}/></label>
        <label>OpenPose 출력 크기 (%) <input type="number" required min="10" max="100" step="0.5" value={inputs.openpose_scale_percent}
          onChange={e=>edit("openpose_scale_percent",e.target.value)}/></label>
        {[["post_processing","공식 후처리"],["remove_horizontal_motion","수평 이동 제거"],["pose_include_hands","손 포즈 포함"],
          ["pose_include_face","얼굴 포즈 포함"]].map(([field,label])=>
          <label key={field}><input type="checkbox" disabled={Boolean(placement) && ["post_processing","remove_horizontal_motion"].includes(field)} checked={inputs[field]} onChange={e=>edit(field,e.target.checked)}/>{label}</label>)}
        {placement && <p>키프레임 좌표를 유지하기 위해 공식 후처리를 켜고 수평 이동 제거를 끕니다.</p>}
      </details>
      <button>생성 요청 검토</button>
    </fieldset></form>}
    {reviewed && <section className="kimodo-request-review" aria-label="생성 요청 확인">
      <h3>생성 요청 확인</h3><p>아직 생성이 시작되지 않았습니다. 입력을 확인한 뒤 대기열에 추가하세요.</p>
      <dl><div><dt>생성 방식</dt><dd>{reviewed.segment_frames?.length ? "순차 생성 · "+reviewed.segment_frames.join(" + ")+"프레임" : "일반 생성"}</dd></div>
        <div><dt>전체 프레임</dt><dd>{reviewed.frames}프레임</dd></div><div><dt>생성 단계</dt><dd>{reviewed.steps}단계</dd></div><div><dt>시드</dt><dd>{reviewed.seed}</dd></div>
        <div><dt>출력 방향</dt><dd>{reviewed.directions?.map(id=>directions[id]?.label || id).join(", ") || "없음"}</dd></div>
        <div><dt>참조 이미지</dt><dd>{references.length ? references.map(file=>file.name).join(", ") : "없음"}</dd></div>
        {reviewed.keyframes?.length>0 && <div><dt>키프레임</dt><dd>{reviewed.keyframes.length}개</dd></div>}</dl>
      <h4>동작 설명</h4><p className="kimodo-review-prompt">{reviewed.prompt}</p><PromptWordCount text={reviewed.prompt} label="최종"/>
      <details><summary>전체 설정 보기</summary><pre>{JSON.stringify(reviewed,(key,value)=>key==="proportion_images"?references.map(file=>file.name):key==="proportion_reviewed_multiview"?bundle?.name || "첨부됨":key==="proportion_face_anchor_calibration"?calibration?.name || "첨부됨":value,2)}</pre></details>
      {handoffReview && <p>동의하면 진행 중인 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 Kimodo를 실행합니다. 작업이 끝나면 Qwen 3.8을 다시 GPU에 적재합니다.</p>}
      <GenerationReviewActions busy={busy} disabledReason={handoffId ? "이전 GPU 양도 상태를 먼저 확인하세요." : ""} onCancel={()=>{setReview(null);setHandoffReview(null);}} onConfirm={()=>perform(handoffReview ? submitHandoff : submit)} confirmLabel={handoffReview ? "해제·생성·재적재에 동의" : "확인 후 대기열에 추가"}/></section>}
    </div>
    {notice && <p role="status">{notice}</p>}
  </section>;
}
