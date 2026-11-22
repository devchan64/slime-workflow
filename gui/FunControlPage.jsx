import GenerationReviewActions from "./GenerationReviewActions.jsx";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import ActionButton from "./ActionButton.jsx";
import React,{useEffect,useRef,useState} from "react";
import {referencePng,videoData} from "./videoInputs.js";
import GeneratorHistory from "./GeneratorHistory.jsx";
import SavedGeneratorInputs from "./SavedGeneratorInputs.jsx";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import GeneratorPageHeader from "./GeneratorPageHeader.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";

import GpuQueueSummary from "./GpuQueueSummary.jsx";
import {FunControlFields,FunControlResult} from "./FunControlSchema.jsx";
import {managementCommand} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import JobIdentifier from "./JobIdentifier.jsx";
import {validateGpuHandoffStatus} from "./validateGpuHandoffStatus.mjs";
import {generationProposalScope,readGenerationProposal,funProposalInputs} from "./generationProposal.mjs";

function validFunInput(record,id,{saved=false}={}){
  const request=record?.request,video=record?.video;
  return Boolean(record?.id===id && request && request.action==="generate" && request.control_type==="pose" && request.width===832 && request.height===480 &&
    typeof request.prompt==="string" && request.prompt.trim() && typeof request.negative_prompt==="string" &&
    (saved ? ["wan22-14b","wan21-1.3b"].includes(request.model_profile) : request.model_profile==null || ["wan22-14b","wan21-1.3b"].includes(request.model_profile)) &&
    Number.isInteger(request.frames) && request.frames>=5 && request.frames<=129 && (request.frames-1)%4===0 &&
    Number.isInteger(request.steps) && request.steps>=2 && request.steps<=100 && Number.isInteger(request.seed) && request.seed>=0 && request.seed<=2147483647 &&
    Number.isFinite(request.flow_shift) && request.flow_shift>=0.1 && request.flow_shift<=20 && Number.isFinite(request.guidance_scale) && request.guidance_scale>=1 && request.guidance_scale<=10 && Number.isFinite(request.switch_ratio) && request.switch_ratio>=0.1 && request.switch_ratio<=0.9 &&
    Array.isArray(request.images) && request.images.length===1 && typeof request.images[0]==="string" && request.images[0].length>0 &&
    typeof request.pose_video==="string" && request.pose_video.length>0 && Number.isInteger(video?.maximum_frames) && video.maximum_frames>=request.frames && typeof video.summary==="string");
}

export default function FunControlPage({embedded=false,session="",restoreFormId="",seedProposal=null,onSaved=()=>{}}){
  const [template,setTemplate]=useState(null),[selected,select]=useState("");
  const [templateRetry,retryTemplate]=useState(0);
  const [templateError,setTemplateError]=useState("");
  const templateRetryRef=useRef(null),templateRetryFocus=useRef(false);
  const [request,setRequest]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const requestRef=useRef(request);requestRef.current=request;
  const attachmentRevision=useRef(0);
  const [loadingInput,setLoadingInput]=useState(false);
  const [pending,setPending]=useState(null),[job,setJob]=useState(embedded ? "" : new URLSearchParams(location.search).get("job") || "");
  const resultRef=useRef(null),focusResult=useRef(false),activeProgressRef=useRef(null);
  useEffect(()=>{if(focusResult.current && job && resultRef.current){focusResult.current=false;resultRef.current.focus();resultRef.current.scrollIntoView({block:"start"});}},[job]);
  const reviewEpoch=useRef(0),interactionRef=useRef({busy,pending});interactionRef.current={busy,pending};
  const [model,setModel]=useState(null);
  const modelReason=(model?.generation_ready ?? model?.ready) ? "" : model ? "모델 준비가 필요합니다. 모델 상태에서 준비 절차를 확인하세요." : "모델 준비 상태를 확인해야 접수할 수 있습니다.";
  const [videoInfo,setVideoInfo]=useState(null);
  const [poseError,setPoseError]=useState("");
  const [sourceSeed,setSourceSeed]=useState(null);
  const [sourceJob,setSourceJob]=useState("");
  const [historyRevision,refreshHistory]=useState(0);
  const [notice,setNotice]=useState("");
  const service="wan22-fun-control";
  const handoffKey=embedded && session ? `fun-gpu-handoff:${session}:${restoreFormId || "draft"}` : "";
  const [handoffReview,setHandoffReview]=useState(null),[handoffId,setHandoffId]=useState(()=>handoffKey ? sessionStorage.getItem(handoffKey) || "" : ""),[handoffStatus,setHandoffStatus]=useState(null);
  useEffect(()=>{if(!handoffId)return;let active=true;managementCommand("hermes-agent","hermes-gpu-handoff-status",{session_id:session,request_id:handoffId}).then(value=>{if(active){validateGpuHandoffStatus(value,session,handoffId,service);setHandoffStatus(value);if(value.job_id)setJob(value.job_id);}}).catch(problem=>{if(active)setError(problem.message);});return()=>{active=false;};},[]);
  async function readJob(id){
    const inputAtStart=requestRef.current,attachmentAtStart=attachmentRevision.current,reviewAtStart=reviewEpoch.current;
    const controller=new AbortController();let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      const response=await fetch("/management/assistant/fun-input/"+encodeURIComponent(id),{cache:"no-store",signal:controller.signal});
      if(!response.ok)throw new Error("이 작업의 입력 사본을 복원할 수 없습니다.");
      let record;try{record=await response.json();}catch(error){if(timedOut)throw error;throw new Error("저장된 입력 형식을 확인할 수 없습니다.");}
      if(!validFunInput(record,id,{saved:true}))throw new Error("저장된 입력 형식을 확인할 수 없습니다.");
      const {images,pose_video,...settings}=record.request;
      return {...record,request:settings,attachments:{images,pose_video},inputAtStart,attachmentAtStart,reviewAtStart};
    }catch(error){if(timedOut)throw new Error("저장 입력 조회 시간이 초과됐습니다. 다시 조회하세요.");throw error;}
    finally{clearTimeout(timeout);}
  }
  function restore(settings,record){
    if(record.reviewAtStart!==reviewEpoch.current || interactionRef.current.busy || interactionRef.current.pending)throw new Error("조회 중 생성 폼에서 다른 작업이 진행되어 이력 입력을 적용하지 않았습니다.");
    if(record.inputAtStart!==requestRef.current || record.attachmentAtStart!==attachmentRevision.current)throw new Error("입력 조회 중 작성 내용이 변경되어 적용하지 않았습니다.");
    setRequest({...settings,...record.attachments});setVideoInfo(record.video);setSourceSeed(Number(settings.seed));setSourceJob(record.id);
    setNotice(record.id+" 입력을 복원했습니다.");requestAnimationFrame(()=>formRef.current?.focus());
  }
  function cleaned(message){setJob("");setNotice(message);refreshHistory(n=>n+1);}
  const sending=useRef(false),formRef=useRef(null),reviewRef=useRef(null);
  const poseInspection=useRef(null),inputLoading=useRef(null);
  useEffect(()=>()=>{poseInspection.current?.abort();inputLoading.current?.abort();},[]);
  useEffect(()=>{if(pending)reviewRef.current?.focus();},[pending]);
  useEffect(()=>{
    if(!templateRetryFocus.current || (!template && !templateError))return;
    templateRetryFocus.current=false;
    requestAnimationFrame(()=>{if(document.activeElement===document.body)(template ? formRef.current : templateRetryRef.current)?.focus();});
  },[template,templateError]);
  const saveAttempt=useRef(null);
  async function saveForm(value=request){
    value={...value,...Object.fromEntries(["frames","steps","seed","flow_shift","guidance_scale","switch_ratio"].map(key=>[key,Number(value[key])]))};
    const serialized=JSON.stringify({request:value,video_info:videoInfo});
    if(!saveAttempt.current || saveAttempt.current.serialized!==serialized)
      saveAttempt.current={id:crypto.randomUUID().replaceAll("-",""),serialized};
    const form_id=saveAttempt.current.id;
    await managementCommand("hermes-agent","hermes-video-form-save",{session_id:session,form_id,request:value,video_info:videoInfo});
    onSaved(); return form_id;
  }
  async function saveDraft(){
    setBusy(true);setError("");
    try{await saveForm();setNotice("생성 폼을 대화에 저장했습니다.");}catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  async function submit(){
    if(!pending || sending.current || modelReason)return;
    sending.current=true;setBusy(true);setError("");
    try{
      if(handoffReview){
        const id=crypto.randomUUID().replaceAll("-","");
        sessionStorage.setItem(handoffKey,id);setHandoffId(id);setHandoffStatus({state:"checking"});
        const result=await managementCommand("hermes-agent","hermes-gpu-handoff-approve",{request_id:id,session_id:session,resident_id:handoffReview.resident_id,service,request:pending,review_hash:handoffReview.review_hash,confirmed:true});
        validateGpuHandoffStatus(result,session,id,service);
        if(!["approved","waiting_release","submitting","running","reload_queued","reloading","ready"].includes(result.state))throw new Error("GPU 양도 접수 여부를 확인할 수 없습니다.");
        setHandoffStatus(result);setNotice("확인한 GPU 양도 요청을 접수했습니다. 진행 상태를 확인하세요.");
        return;
      }
      const form_id=embedded ? await saveForm(pending) : null;
      const result=embedded ? await managementCommand("hermes-agent","hermes-video-form-submit",{session_id:session,form_id}) : await managementCommand("wan22-fun-control","generate",pending);
      if(embedded && result.state!=="accepted")throw new Error("접수 결과 확인 필요 · 저장된 메시지에서 상태를 확인하세요.");
      const jobId=embedded ? result.job_id : result.id;
      if(!jobId)throw new Error("작업 ID를 확인할 수 없습니다.");
      setJob(jobId);onSaved();
    }catch(problem){setError(problem.message+(handoffReview ? " · GPU 양도 상태를 확인하세요." : " · 다시 접수하기 전에 이력을 확인하세요."));}
    finally{sending.current=false;setPending(null);setHandoffReview(null);setBusy(false);}
  }
  useEffect(()=>{
    const controller=new AbortController();
    let active=true,timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setTemplateError("");
    fetch("/management/assistant/fun-template",{signal:controller.signal}).then(async response=>{
      if(!response.ok)throw new Error("예제 목록 조회 실패");
      const data=await response.json();
      if(!data || !data.defaults || ![data.defaults.frames,data.defaults.steps,data.defaults.seed,data.defaults.flow_shift,data.defaults.guidance_scale,data.defaults.switch_ratio].every(Number.isFinite) ||
        !Number.isInteger(data.maximum_frames) || data.maximum_frames<5 || !Number.isInteger(data.maximum_seed) || data.maximum_seed<0 ||
        !Array.isArray(data.models) || !data.models.length || data.models.some(item=>!item || typeof item.id!=="string" || typeof item.label!=="string") ||
        !data.models.some(item=>item.id===data.defaults.model_profile) ||
        !Array.isArray(data.examples) || data.examples.some(item=>!item || typeof item.id!=="string" || typeof item.label!=="string"))throw new Error("생성 입력 설정 형식을 확인할 수 없습니다.");
      clearTimeout(timeout);
      let initial={...data.defaults,action:"generate",control_type:"pose",width:832,height:480,images:[],pose_video:"",prompt:"",negative_prompt:""};
      if(!embedded){
        try{
          const scope=generationProposalScope(location.search,session || new URLSearchParams(location.search).get('session') || '', 'video');
          if(scope){initial=funProposalInputs(initial,await readGenerationProposal(managementCommand,scope));if(!controller.signal.aborted)setNotice('대화 제안을 불러왔습니다. 참조 이미지와 처리된 포즈 영상을 선택하세요.');}
        }catch(problem){if(!controller.signal.aborted)setError('대화 제안을 불러오지 못했습니다 · '+problem.message);}
      }
      if(!controller.signal.aborted){setTemplate(data);setRequest(current=>current ?? initial);select(data.examples[0]?.id || "");}
    }).catch(problem=>{if(active && (timedOut || !controller.signal.aborted))setTemplateError(timedOut ? "생성 입력 조회 시간이 초과됐습니다." : requestErrorMessage(problem));}).finally(()=>clearTimeout(timeout));
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[templateRetry]);
  useEffect(()=>{
    if(!embedded || !session || !restoreFormId || !template)return;
    let active=true;setBusy(true);setError("");
    managementCommand("hermes-agent","hermes-video-form-read",{session_id:session,form_id:restoreFormId}).then(record=>{
      if(active){setRequest(record.request);setVideoInfo(record.video_info);setSourceSeed(null);setSourceJob("");setJob("");setNotice("대화에 저장된 폼을 불러왔습니다. 변경하면 새 메시지로 저장됩니다.");saveAttempt.current={id:restoreFormId,serialized:JSON.stringify({request:record.request,video_info:record.video_info})};}
    }).catch(problem=>{if(active)setError(problem.message);}).finally(()=>{if(active)setBusy(false);});
    return ()=>{active=false;};
  },[embedded,session,restoreFormId,template]);
  useEffect(()=>{
    if(!embedded || !seedProposal || !template)return;
    const controller=new AbortController();setBusy(true);setError("");
    (async()=>{
      const response=await fetch("/management/assistant/fun-input/"+encodeURIComponent(seedProposal.job_id),{signal:controller.signal,cache:"no-store"});
      if(!response.ok)throw new Error("원본 작업 입력을 확인할 수 없습니다. 생성 이력에서 입력을 직접 선택하세요.");
      const record=await response.json();
      if(record.id!==seedProposal.job_id || !record.request || !Number.isInteger(record.request.seed) || record.request.seed<0 || record.request.seed>2147483647)
        throw new Error("원본 작업의 입력이나 시드를 확인할 수 없습니다.");
      let next=seedProposal.reuse ? record.request.seed : seedProposal.seed;
      if(next==null){next=crypto.getRandomValues(new Uint32Array(1))[0] & 0x7fffffff;if(next===record.request.seed)next=(next+1)%2147483648;}
      if(!Number.isInteger(next) || next<0 || next>2147483647)throw new Error("제안한 시드가 허용 범위를 벗어났습니다.");
      if(!controller.signal.aborted){setRequest({...record.request,seed:next});setVideoInfo(record.video);setSourceSeed(record.request.seed);setSourceJob(record.id);setJob("");saveAttempt.current=null;
        setNotice("원본 "+record.id+"의 입력을 불러왔습니다. "+(seedProposal.reuse ? "입력을 확인하세요." : next===record.request.seed ? "원본과 같은 시드입니다. 변경 후 검토하세요." : "입력과 새 시드를 확인하세요."));}
    })().catch(problem=>{if(!controller.signal.aborted)setError(problem.message);}).finally(()=>{if(!controller.signal.aborted)setBusy(false);});
    return ()=>controller.abort();
  },[embedded,seedProposal,template]);
  async function attach(file,field){
    if(!file)return false;
    attachmentRevision.current++;
    setBusy(true);setError("");
    if(field==="pose_video")setPoseError("");
    let timeout,controller,timedOut=false;
    try{
      const value=field==="images"?[await referencePng(file)]:await videoData(file);
      if(field==="pose_video"){
        controller=new AbortController();poseInspection.current=controller;
        timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
        const response=await fetch("/management/assistant/fun-video-info",{method:"POST",body:file,signal:controller.signal});
        const info=await response.json();
        if(!response.ok)throw new Error(info.summary || "포즈 영상을 확인할 수 없습니다.");
        if(!Number.isInteger(info.maximum_frames) || info.maximum_frames<1 || typeof info.summary!=="string")throw new Error("포즈 영상 정보를 확인할 수 없습니다. 다시 선택하세요.");
        setVideoInfo(info);
      }
      setRequest(current=>({...current,[field]:value}));
      return true;
    }catch(problem){const message=timedOut ? "포즈 영상 정보 조회 시간이 초과됐습니다. 다시 선택하세요." : requestErrorMessage(problem);setError(message);if(field==="pose_video")setPoseError(message);return false;}
    finally{clearTimeout(timeout);if(poseInspection.current===controller)poseInspection.current=null;setBusy(false);}
  }
  async function load(restore=false){
    const focused=formRef.current?.contains(document.activeElement) ? document.activeElement : null;
    setBusy(true);setLoadingInput(true);setError("");
    const controller=new AbortController();inputLoading.current=controller;let timedOut=false,applied=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      const id=restore?job:selected;
      const response=await fetch("/management/assistant/"+(restore?"fun-input/":"fun-example/")+encodeURIComponent(id),{signal:controller.signal});
      if(!response.ok)throw new Error(restore?"이 작업의 입력 사본을 복원할 수 없습니다.":"예제 첨부 파일을 불러올 수 없습니다.");
      let example;try{example=await response.json();}catch(error){if(timedOut)throw error;throw new Error(restore ? "저장된 입력 형식을 확인할 수 없습니다." : "예제 입력 형식을 확인할 수 없습니다.");}
      if(!validFunInput(example,id,{saved:restore}))throw new Error(restore ? "저장된 입력 형식을 확인할 수 없습니다." : "예제 입력 형식을 확인할 수 없습니다.");
      setVideoInfo(example.video);setSourceSeed(restore ? Number(example.request.seed) : null);setSourceJob(restore ? example.id : "");
      setRequest(example.request);applied=true;
    }catch(problem){if(!controller.signal.aborted || timedOut)setError(timedOut ? "입력 조회 시간이 초과됐습니다. 다시 시도하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timeout);if(inputLoading.current===controller)inputLoading.current=null;setLoadingInput(false);setBusy(false);if(focused)requestAnimationFrame(()=>{if(document.activeElement===document.body)(applied ? formRef.current : focused)?.focus({preventScroll:true});});}
  }
  const frameLimit=videoInfo?.maximum_frames ?? template?.maximum_frames;
  const settings=[
    ["frames","프레임 수",5,frameLimit,4],
    ["steps","스텝",2,100,1],
    ["seed","시드",0,template?.maximum_seed,1],
    ["flow_shift","Flow shift",0.1,20,"any"],
    ["guidance_scale","Guidance scale",1,10,"any"],
    ["switch_ratio","모델 전환 비율",0.1,0.9,"any"],
  ];
  async function review(event){
    reviewEpoch.current++;
    event.preventDefault();
    const values=Object.fromEntries(settings.map(([key])=>[key,Number(request[key])]));
    const reviewed={...request,...values};setBusy(true);setError("");setHandoffReview(null);
    try{
      if(embedded && session){
        const owner=await managementCommand("hermes-agent","hermes-resident-status",{session_id:session});
        if(owner.session_id!==session || !owner.resident)throw new Error("대화 모델 상태를 확인할 수 없습니다.");
        if(owner.resident_id){
          if(owner.resident.state!=="ready")throw new Error("Qwen 3.8 상주 모델 상태를 확인한 뒤 다시 검토하세요.");
          const handoff=await managementCommand("hermes-agent","hermes-gpu-handoff-preview",{session_id:session,resident_id:owner.resident_id,service,request:reviewed});
          if(handoff.session_id!==session || handoff.resident_id!==owner.resident_id || handoff.service!==service || !/^[a-f0-9]{64}$/.test(handoff.review_hash || ""))throw new Error("GPU 양도 검토 결과가 일치하지 않습니다.");
          setHandoffReview(handoff);
        }else if(owner.resident.state!=="not_found")throw new Error("대화 모델 상태를 확인할 수 없습니다.");
      }
      setPending(reviewed);
    }catch(problem){setError(problem.message);}finally{setBusy(false);}
  }
  function renderResult(id){
    return <><SavedGeneratorInputs id={id} service={service} readJob={readJob}/><FunControlResult key={id} job={id} folderLink={embedded}>
      {(record,reload)=>record && <React.Fragment key={record.status}>
        <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>
      </React.Fragment>}
    </FunControlResult></>;
  }
  return <article className={"fun-control-page"+(embedded?" fun-embedded":"")}>
    <GeneratorPageHeader title="Wan Fun Control 영상 생성"
      description="참조 이미지의 외형과 포즈 영상의 움직임으로 영상을 만듭니다."
      generator="wan22-fun-control-generator" service={service} model={model} onStatus={setModel} embedded={embedded}/>
    {handoffId && <GpuHandoffStatus session={session} id={handoffId} service={service} status={handoffStatus} onUpdate={value=>{setHandoffStatus(value);if(value.job_id)setJob(value.job_id);}}
      onClose={()=>{sessionStorage.removeItem(handoffKey);setHandoffId("");setHandoffStatus(null);}}/>}
    <div ref={activeProgressRef}><ActiveGeneratorProgress service={service} revision={historyRevision+":"+job} onOpenResult={id=>{if(id===job){resultRef.current?.focus();resultRef.current?.scrollIntoView({block:"start"});}else{focusResult.current=true;setJob(id);}}}/></div>
    {template && request && <form ref={formRef} tabIndex={-1} aria-label="생성 입력" onSubmit={review} onInvalid={event=>{const details=event.target.closest("details");if(details)details.open=true;}}><fieldset disabled={busy || !!pending || Boolean(handoffId)}><legend>생성 입력</legend>
    <fieldset className="fun-source" disabled={busy || !!pending || !template}><legend>원본 작업</legend>
      {loadingInput && <p role="status">입력을 불러오고 있습니다. 현재 입력은 유지됩니다.</p>}
      {sourceJob ? <><p>불러온 원본 작업</p><JobIdentifier id={sourceJob} compact/></> : <p>선택된 원본 작업이 없습니다.</p>}
      {job && <div>{sourceJob!==job && <><p>현재 작업</p><JobIdentifier id={job} compact/></>}<button type="button" disabled={!template} onClick={()=>load(true)}>현재 작업 입력으로 교체</button></div>}
      <details><summary>제작 예제 사용</summary><label>예제 선택<select value={selected} onChange={event=>select(event.target.value)}>
        {template?.examples.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        <button type="button" disabled={!selected} onClick={()=>load()}>선택한 예제로 입력 교체</button></details>
    </fieldset>
      <FunControlFields request={request} setRequest={setRequest} attach={attach} onImageSelectionStart={()=>{attachmentRevision.current++;}} removePose={()=>{setRequest(current=>({...current,pose_video:""}));setVideoInfo(null);setError(current=>current===poseError?"":current);setPoseError("");}} videoInfo={videoInfo} frameLimit={frameLimit} template={template} sourceSeed={sourceSeed} busy={busy || !!pending}/>
      {embedded && <button type="button" onClick={saveDraft}>폼을 대화에 저장</button>}
      <ActionButton type="submit" reasons={[
        !request.prompt.trim() && "동작 프롬프트를 입력하세요.",
        !request.images[0] && "외형 참조 이미지를 선택하세요.",
        !request.pose_video && "포즈 영상을 선택하세요."
      ]}>생성 요청 검토</ActionButton>
    </fieldset></form>}
    {pending && <section ref={reviewRef} tabIndex={-1} className="fun-request-review" aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/>
      <p>모델 · {template?.models?.find(item=>item.id===(pending.model_profile || "wan22-14b"))?.label || pending.model_profile || "wan22-14b"}</p>
      <p>외형 참조 이미지 + 포즈 영상 · {pending.frames}프레임 · 16fps · {(pending.frames/16).toFixed(2)}초 · {pending.steps}스텝 · 시드 {pending.seed}</p>
      <p>{videoInfo?.summary || "입력 영상 정보 확인 중"}</p><h3>동작 프롬프트</h3><p className="fun-review-prompt">{pending.prompt}</p>
      <h3>부정 프롬프트</h3><p className="fun-review-prompt">{pending.negative_prompt || "없음"}</p>
      {handoffReview && <p>동의하면 진행 중인 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 영상을 생성합니다. 작업이 끝나면 Qwen 3.8을 다시 GPU에 적재합니다.</p>}
      <GenerationReviewActions disabledReason={modelReason || (handoffId ? "이전 GPU 양도 상태를 먼저 확인하세요." : "")} busy={busy} onCancel={()=>{setPending(null);setHandoffReview(null);requestAnimationFrame(()=>formRef.current?.querySelector("textarea")?.focus());}} onConfirm={submit} confirmLabel={handoffReview ? "해제·생성·재적재에 동의" : "확인 후 대기열에 추가"}/>
    </section>}
    {error && <p role="alert">{error}</p>}
    {templateError && <p role="alert">{templateError}</p>}
    {!template && !templateError && <p role="status">생성 입력을 불러오는 중입니다.</p>}
    {!template && templateError && <button ref={templateRetryRef} type="button" onClick={()=>{templateRetryFocus.current=true;retryTemplate(value=>value+1);}}>생성 입력 다시 불러오기</button>}
    {notice && <p role="status">{notice}</p>}
    <fieldset className="fun-history" aria-label="작업 이력" disabled={busy || !!pending}>
      <GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id)setJob("");if(sourceJob===id)setSourceJob("");setNotice(message);}} key={historyRevision} service={service} readJob={readJob} restore={restore} renderResult={renderResult}/>
      <HistoryCleanup allowSelected={false} service={service} onDeleted={cleaned}/>
    </fieldset>
    {job && <section ref={resultRef} tabIndex={-1} aria-label="현재 작업 결과"><button type="button" onClick={()=>{const closedId=job;setJob("");requestAnimationFrame(()=>{const row=[...activeProgressRef.current?.querySelectorAll('.active-generator-job') || []].find(item=>item.textContent.includes(closedId));const button=[...row?.querySelectorAll('button') || []].find(item=>item.textContent==='작업 결과 보기');(button || activeProgressRef.current?.querySelector('summary'))?.focus();});}}>결과 닫기</button>{renderResult(job)}</section>}
  </article>;
}
