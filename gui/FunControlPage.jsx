import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ReviewPrompt from "./ReviewPrompt.jsx";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
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
import GeneratorSectionNavigation from "./GeneratorSectionNavigation.jsx";

import GpuQueueSummary from "./GpuQueueSummary.jsx";
import {FunControlFields,FunControlResult} from "./FunControlSchema.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
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

export function validFunForm(record,id){
  const request=record?.request,info=record?.video_info;
  return Boolean(record?.form_id===id && request && typeof request==='object' && !Array.isArray(request) &&
    Array.isArray(request.images) && request.images.length<=1 && request.images.every(value=>typeof value==='string') &&
    typeof request.pose_video==='string' && ['prompt','negative_prompt'].every(key=>typeof request[key]==='string') &&
    ['frames','steps','seed','flow_shift','guidance_scale','switch_ratio'].every(key=>Number.isFinite(request[key])) &&
    (info===null || (typeof info==='object' && !Array.isArray(info))));
}

export default function FunControlPage({embedded=false,session="",restoreFormId="",seedProposal=null,onSaved=()=>{}}){
  const [template,setTemplate]=useState(null),[selected,select]=useState("");
  const [templateRetry,retryTemplate]=useState(0);
  const [templateError,setTemplateError]=useState("");
  const [restoreError,setRestoreError]=useState(""),[restoreRevision,retryRestore]=useState(0);
  const [seedError,setSeedError]=useState(""),[seedRevision,retrySeed]=useState(0);
  const templateRetryRef=useRef(null),templateRetryFocus=useRef(false),restoreRetryRef=useRef(null),restoreRetryFocus=useRef(false),restorePending=useRef(false),seedRetryRef=useRef(null),seedRetryFocus=useRef(false),seedPending=useRef(false);
  const [request,setRequestState]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const requestRef=useRef(request);requestRef.current=request;
  function setRequest(value){const next=typeof value==="function" ? value(requestRef.current) : value;requestRef.current=next;setRequestState(next);}
  const attachmentRevision=useRef(0),imageChecking=useRef(false),attachmentProcessing=useRef(false);
  const [imageCheckPending,setImageCheckPending]=useState(false);
  const [loadingInput,setLoadingInput]=useState(false);
  const [pending,setPending]=useState(null),[job,setJobState]=useState(embedded ? "" : new URLSearchParams(location.search).get("job") || "");
  const jobEpoch=useRef(0);function setJob(value){jobEpoch.current++;setJobState(value);}
  const resultRef=useRef(null),historyRef=useRef(null),focusResult=useRef(null),resultFocusFrame=useRef(null),activeProgressRef=useRef(null);
  useEffect(()=>{const focus=focusResult.current;if(!focus || !job || !resultRef.current)return;focusResult.current=null;if(focus.id===job && (document.activeElement===document.body || document.activeElement===focus.origin)){resultRef.current.focus();resultRef.current.scrollIntoView({block:"start"});}},[job]);
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
  async function readJob(id,{signal}={}){
    const inputAtStart=requestRef.current,attachmentAtStart=attachmentRevision.current,checkingAtStart=imageChecking.current || attachmentProcessing.current,reviewAtStart=reviewEpoch.current,focusAtStart=document.activeElement;
    const controller=new AbortController();let timedOut=false;
    const abort=()=>controller.abort();if(signal?.aborted)controller.abort();else signal?.addEventListener('abort',abort,{once:true});
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      const response=await untilAborted(fetch("/management/assistant/fun-input/"+encodeURIComponent(id),{cache:"no-store",signal:controller.signal}),controller.signal);
      if(!response.ok)throw new Error("이 작업의 입력 사본을 복원할 수 없습니다.");
      let record;try{record=await untilAborted(response.json(),controller.signal);}catch(error){if(controller.signal.aborted)throw error;throw new Error("저장된 입력 형식을 확인할 수 없습니다.");}
      if(!validFunInput(record,id,{saved:true}))throw new Error("저장된 입력 형식을 확인할 수 없습니다.");
      const {images,pose_video,...settings}=record.request;
      return {...record,request:settings,attachments:{images,pose_video},inputAtStart,attachmentAtStart,checkingAtStart,reviewAtStart,focusAtStart};
    }catch(error){if(timedOut)throw new Error("저장 입력 조회 시간이 초과됐습니다. 다시 조회하세요.");throw error;}
    finally{clearTimeout(timeout);signal?.removeEventListener('abort',abort);}
  }
  function restore(settings,record){
    if(record.reviewAtStart!==reviewEpoch.current || interactionRef.current.busy || interactionRef.current.pending)throw new Error("조회 중 생성 폼에서 다른 작업이 진행되어 이력 입력을 적용하지 않았습니다.");
    if(record.checkingAtStart || imageChecking.current || attachmentProcessing.current || record.inputAtStart!==requestRef.current || record.attachmentAtStart!==attachmentRevision.current)throw new Error("첨부 확인 중이거나 조회 중 입력이 변경되어 적용하지 않았습니다. 확인 후 다시 시도하세요.");
    const restored={...settings,...record.attachments};setRequest(restored);setVideoInfo(record.video);setSourceSeed(Number(settings.seed));setSourceJob(record.id);
    setNotice(record.id+" 입력을 복원했습니다.");if(restoreFrame.current!==null)cancelAnimationFrame(restoreFrame.current);
    restoreFrame.current=requestAnimationFrame(()=>{restoreFrame.current=null;if(record.reviewAtStart===reviewEpoch.current && !interactionRef.current.busy && !interactionRef.current.pending && (document.activeElement===document.body || document.activeElement===record.focusAtStart) && formRef.current?.isConnected)formRef.current.focus();});
  }
  function cleaned(message){setJob("");setNotice(message);refreshHistory(n=>n+1);}
  const sending=useRef(false),formRef=useRef(null),reviewRef=useRef(null),reviewOrigin=useRef(null),reviewRequest=useRef(null),restoreFrame=useRef(null);
  const poseInspection=useRef(null),inputLoading=useRef(null),saveRequest=useRef(null),attachmentEpoch=useRef(0),mounted=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;attachmentEpoch.current++;poseInspection.current?.abort();inputLoading.current?.abort();saveRequest.current?.abort();const review=reviewRequest.current;reviewRequest.current=null;review?.abort();if(restoreFrame.current!==null)cancelAnimationFrame(restoreFrame.current);if(resultFocusFrame.current!==null)cancelAnimationFrame(resultFocusFrame.current);};},[]);
  useEffect(()=>{if(pending && (document.activeElement===document.body || document.activeElement===reviewOrigin.current))reviewRef.current?.focus();},[pending]);
  useEffect(()=>{
    if(!templateRetryFocus.current || (!template && !templateError))return;
    templateRetryFocus.current=false;
    requestAnimationFrame(()=>{if(document.activeElement===document.body)(template ? formRef.current : templateRetryRef.current)?.focus();});
  },[template,templateError]);
  const saveAttempt=useRef(null);
  async function saveForm(value=requestRef.current){
    value={...value,...Object.fromEntries(["frames","steps","seed","flow_shift","guidance_scale","switch_ratio"].map(key=>[key,Number(value[key])]))};
    const serialized=JSON.stringify({request:value,video_info:videoInfo});
    if(!saveAttempt.current || saveAttempt.current.serialized!==serialized)
      saveAttempt.current={id:crypto.randomUUID().replaceAll("-",""),serialized};
    const form_id=saveAttempt.current.id;
    const controller=new AbortController();saveRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{await untilAborted(managementCommand("hermes-agent","hermes-video-form-save",{session_id:session,form_id,request:value,video_info:videoInfo},{signal:controller.signal}),controller.signal);}
    catch(problem){if(timedOut)throw new Error("폼 저장 응답 시간이 초과됐습니다. 대화 이력에서 저장 여부를 확인하세요.");throw problem;}
    finally{clearTimeout(timeout);if(saveRequest.current===controller)saveRequest.current=null;}
    return form_id;
  }
  async function saveDraft(){
    if(sending.current || reviewRequest.current || interactionRef.current.busy || interactionRef.current.pending)return;
    if(imageChecking.current || attachmentProcessing.current){setError("첨부 확인이 끝난 뒤 폼을 저장하세요.");return;}
    sending.current=true;setBusy(true);setError("");
    try{await saveForm();if(mounted.current){onSaved();setNotice("생성 폼을 대화에 저장했습니다.");}}catch(problem){if(mounted.current)setError(problem.message);}
    finally{if(mounted.current){sending.current=false;setBusy(false);}}
  }
  async function submit(){
    if(!pending || sending.current || modelReason)return;
    sending.current=true;setBusy(true);setError("");let savedForm=false;
    try{
      if(handoffReview){
        const id=crypto.randomUUID().replaceAll("-","");
        sessionStorage.setItem(handoffKey,id);setHandoffId(id);setHandoffStatus({state:"checking"});
        const result=await managementCommand("hermes-agent","hermes-gpu-handoff-approve",{request_id:id,session_id:session,resident_id:handoffReview.resident_id,service,request:pending,review_hash:handoffReview.review_hash,confirmed:true});
        if(!mounted.current)return;
        validateGpuHandoffStatus(result,session,id,service);
        if(!["approved","waiting_release","submitting","running","reload_queued","reloading","ready"].includes(result.state))throw new Error("GPU 양도 접수 여부를 확인할 수 없습니다.");
        setHandoffStatus(result);setNotice("확인한 GPU 양도 요청을 접수했습니다. 진행 상태를 확인하세요.");
        return;
      }
      const form_id=embedded ? await saveForm(pending) : null;if(embedded)savedForm=true;
      if(!mounted.current)return;
      const result=embedded ? await managementCommand("hermes-agent","hermes-video-form-submit",{session_id:session,form_id}) : await managementCommand("wan22-fun-control","generate",pending);
      if(!mounted.current)return;
      if(embedded && result.state!=="accepted")throw new Error("접수 결과 확인 필요 · 저장된 메시지에서 상태를 확인하세요.");
      const jobId=embedded ? result.job_id : result.id;
      if(!jobId)throw new Error("작업 ID를 확인할 수 없습니다.");
      setJob(jobId);onSaved();
    }catch(problem){if(mounted.current){if(savedForm)onSaved();setError(problem.message+(handoffReview ? " · GPU 양도 상태를 확인하세요." : " · 다시 접수하기 전에 이력을 확인하세요."));}}
    finally{if(mounted.current){sending.current=false;setPending(null);setHandoffReview(null);setBusy(false);}}
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
          if(scope){initial=funProposalInputs(initial,await readGenerationProposal(managementCommand,scope,{signal:controller.signal}));if(!controller.signal.aborted)setNotice('대화 제안을 불러왔습니다. 참조 이미지와 처리된 포즈 영상을 선택하세요.');}
        }catch(problem){if(!controller.signal.aborted)setError('대화 제안을 불러오지 못했습니다 · '+problem.message);}
      }
      if(!controller.signal.aborted){setTemplate(data);setRequest(current=>current ?? initial);select(data.examples[0]?.id || "");}
    }).catch(problem=>{if(active && (timedOut || !controller.signal.aborted))setTemplateError(timedOut ? "생성 입력 조회 시간이 초과됐습니다." : requestErrorMessage(problem));}).finally(()=>clearTimeout(timeout));
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[templateRetry]);
  useEffect(()=>{
    if(!embedded || !session || !restoreFormId || !template)return;
    let active=true,timedOut=false;const controller=new AbortController(),inputAtStart=requestRef.current,attachmentAtStart=attachmentRevision.current,reviewAtStart=reviewEpoch.current;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);restorePending.current=true;setBusy(true);setRestoreError("");
    untilAborted(managementCommand("hermes-agent","hermes-video-form-read",{session_id:session,form_id:restoreFormId},{signal:controller.signal}),controller.signal).then(record=>{
      if(!validFunForm(record,restoreFormId))throw new Error("저장된 폼의 입력 형식을 확인할 수 없습니다.");
      if(requestRef.current!==inputAtStart || attachmentRevision.current!==attachmentAtStart || reviewEpoch.current!==reviewAtStart)throw new Error("조회 중 입력이 변경되어 저장 폼을 적용하지 않았습니다.");
      if(active){setRequest(record.request);setVideoInfo(record.video_info);setSourceSeed(null);setSourceJob("");setJob("");setNotice("대화에 저장된 폼을 불러왔습니다. 변경하면 새 메시지로 저장됩니다.");saveAttempt.current={id:restoreFormId,serialized:JSON.stringify({request:record.request,video_info:record.video_info})};}
    }).catch(problem=>{if(active)setRestoreError((timedOut ? "저장 폼 조회 시간이 초과됐습니다." : requestErrorMessage(problem))+" 현재 입력은 유지됩니다.");}).finally(()=>{clearTimeout(timeout);if(active){restorePending.current=false;setBusy(false);}});
    return ()=>{active=false;restorePending.current=false;clearTimeout(timeout);controller.abort();};
  },[embedded,session,restoreFormId,template,restoreRevision]);
  useEffect(()=>{if(busy || !restoreRetryFocus.current)return;restoreRetryFocus.current=false;const target=restoreError ? restoreRetryRef.current : formRef.current;if(document.activeElement===document.body && target?.isConnected && !target.matches(':disabled'))target.focus();},[busy,restoreError]);
  useEffect(()=>{
    if(!embedded || !seedProposal || !template)return;
    let active=true,timedOut=false;const controller=new AbortController(),inputAtStart=requestRef.current,attachmentAtStart=attachmentRevision.current,reviewAtStart=reviewEpoch.current;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);seedPending.current=true;setBusy(true);setSeedError("");
    (async()=>{
      const response=await untilAborted(fetch("/management/assistant/fun-input/"+encodeURIComponent(seedProposal.job_id),{signal:controller.signal,cache:"no-store"}),controller.signal);
      if(!response.ok)throw new Error("원본 작업 입력을 확인할 수 없습니다. 생성 이력에서 입력을 직접 선택하세요.");
      const record=await untilAborted(response.json(),controller.signal);
      if(!validFunInput(record,seedProposal.job_id,{saved:true}))
        throw new Error("원본 작업의 입력이나 시드를 확인할 수 없습니다.");
      if(requestRef.current!==inputAtStart || attachmentRevision.current!==attachmentAtStart || reviewEpoch.current!==reviewAtStart)throw new Error("조회 중 입력이 변경되어 원본 입력을 적용하지 않았습니다.");
      let next=seedProposal.reuse ? record.request.seed : seedProposal.seed;
      if(next==null){next=crypto.getRandomValues(new Uint32Array(1))[0] & 0x7fffffff;if(next===record.request.seed)next=(next+1)%2147483648;}
      if(!Number.isInteger(next) || next<0 || next>2147483647)throw new Error("제안한 시드가 허용 범위를 벗어났습니다.");
      if(!controller.signal.aborted){setRequest({...record.request,seed:next});setVideoInfo(record.video);setSourceSeed(record.request.seed);setSourceJob(record.id);setJob("");saveAttempt.current=null;
        setNotice("원본 "+record.id+"의 입력을 불러왔습니다. "+(seedProposal.reuse ? "입력을 확인하세요." : next===record.request.seed ? "원본과 같은 시드입니다. 변경 후 검토하세요." : "입력과 새 시드를 확인하세요."));}
    })().catch(problem=>{if(active)setSeedError((timedOut ? "원본 입력 조회 시간이 초과됐습니다." : requestErrorMessage(problem))+" 현재 입력은 유지됩니다.");}).finally(()=>{clearTimeout(timeout);if(active){seedPending.current=false;setBusy(false);}});
    return ()=>{active=false;seedPending.current=false;clearTimeout(timeout);controller.abort();};
  },[embedded,seedProposal,template,seedRevision]);
  useEffect(()=>{if(busy || !seedRetryFocus.current)return;seedRetryFocus.current=false;const target=seedError ? seedRetryRef.current : formRef.current;if(document.activeElement===document.body && target?.isConnected && !target.matches(':disabled'))target.focus();},[busy,seedError]);
  async function attach(file,field){
    if(!file)return false;
    const epoch=attachmentEpoch.current;
    attachmentProcessing.current=true;
    attachmentRevision.current++;
    setBusy(true);setError("");
    if(field==="pose_video")setPoseError("");
    let timeout,controller,timedOut=false;
    try{
      const value=field==="images"?[await referencePng(file)]:await videoData(file);
      if(epoch!==attachmentEpoch.current)return false;
      if(field==="pose_video"){
        controller=new AbortController();poseInspection.current=controller;
        timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
        const response=await untilAborted(fetch("/management/assistant/fun-video-info",{method:"POST",body:file,signal:controller.signal}),controller.signal);
        const info=await untilAborted(response.json(),controller.signal);
        if(!response.ok)throw new Error(info.summary || "포즈 영상을 확인할 수 없습니다.");
        if(!Number.isInteger(info.maximum_frames) || info.maximum_frames<1 || typeof info.summary!=="string")throw new Error("포즈 영상 정보를 확인할 수 없습니다. 다시 선택하세요.");
        setVideoInfo(info);
      }
      setRequest(current=>({...current,[field]:value}));
      return true;
    }catch(problem){if(epoch===attachmentEpoch.current){const message=timedOut ? "포즈 영상 정보 조회 시간이 초과됐습니다. 다시 선택하세요." : requestErrorMessage(problem);setError(message);if(field==="pose_video")setPoseError(message);}return false;}
    finally{clearTimeout(timeout);if(poseInspection.current===controller)poseInspection.current=null;if(epoch===attachmentEpoch.current){attachmentProcessing.current=false;setBusy(false);}}
  }
  async function load(restore=false){
    if(imageChecking.current || attachmentProcessing.current){setError("첨부 확인이 끝난 뒤 입력을 교체하세요.");return;}
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
    event.preventDefault();if(reviewRequest.current || interactionRef.current.busy || interactionRef.current.pending)return;
    if(imageChecking.current || attachmentProcessing.current){setError("첨부 확인이 끝난 뒤 생성 요청을 검토하세요.");return;}
    reviewEpoch.current++;
    const controller=new AbortController();reviewRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);reviewOrigin.current=document.activeElement;
    const current=requestRef.current,values=Object.fromEntries(settings.map(([key])=>[key,Number(current[key])]));
    const attachmentAtStart=attachmentRevision.current;
    const reviewed={...current,...values};setBusy(true);setError("");setHandoffReview(null);
    try{
      if(embedded && session){
        const owner=await untilAborted(managementCommand("hermes-agent","hermes-resident-status",{session_id:session},{signal:controller.signal}),controller.signal);
        if(requestRef.current!==current || attachmentRevision.current!==attachmentAtStart)throw new Error("검토 중 입력이 변경되었습니다. 다시 확인하세요.");
        if(owner.session_id!==session || !owner.resident)throw new Error("대화 모델 상태를 확인할 수 없습니다.");
        if(owner.resident_id){
          if(owner.resident.state!=="ready")throw new Error("Qwen 3.8 상주 모델 상태를 확인한 뒤 다시 검토하세요.");
          const handoff=await untilAborted(managementCommand("hermes-agent","hermes-gpu-handoff-preview",{session_id:session,resident_id:owner.resident_id,service,request:reviewed},{signal:controller.signal}),controller.signal);
          if(handoff.session_id!==session || handoff.resident_id!==owner.resident_id || handoff.service!==service || !/^[a-f0-9]{64}$/.test(handoff.review_hash || ""))throw new Error("GPU 양도 검토 결과가 일치하지 않습니다.");
          if(requestRef.current!==current || attachmentRevision.current!==attachmentAtStart)throw new Error("검토 중 입력이 변경되었습니다. 다시 확인하세요.");
          setHandoffReview(handoff);
        }else if(owner.resident.state!=="not_found")throw new Error("대화 모델 상태를 확인할 수 없습니다.");
      }
      if(reviewRequest.current===controller)setPending(reviewed);
    }catch(problem){if(reviewRequest.current===controller){setHandoffReview(null);setError(timedOut ? "생성 요청 검토 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem));}}finally{clearTimeout(timeout);if(reviewRequest.current===controller){reviewRequest.current=null;setBusy(false);}}
  }
  function cancelReview(){const restore=reviewRef.current?.contains(document.activeElement),epoch=reviewEpoch.current;setPending(null);setHandoffReview(null);if(restoreFrame.current!==null)cancelAnimationFrame(restoreFrame.current);if(restore)restoreFrame.current=requestAnimationFrame(()=>{restoreFrame.current=null;const target=formRef.current?.querySelector("textarea");if(epoch===reviewEpoch.current && !reviewRequest.current && target && !target.matches(":disabled"))restoreLostFocus(document,target);});}
  function closeResult(){
    const closedId=job,restore=resultRef.current?.contains(document.activeElement);setJob("");const epoch=jobEpoch.current;
    if(resultFocusFrame.current!==null)cancelAnimationFrame(resultFocusFrame.current);
    if(restore)resultFocusFrame.current=requestAnimationFrame(()=>{resultFocusFrame.current=null;if(epoch!==jobEpoch.current || document.activeElement!==document.body)return;const buttons=[...activeProgressRef.current?.querySelectorAll('button') || []];const target=buttons.find(button=>button.getAttribute('aria-label')===closedId+' 작업 결과 보기') || activeProgressRef.current?.querySelector('summary');if(target?.isConnected && !target.matches(':disabled'))target.focus();});
  }
  function renderResult(id){
    return <><SavedGeneratorInputs id={id} service={service} readJobWithSignal={readJob}/><FunControlResult key={id} job={id} folderLink={embedded}>
      {(record,reload)=>record && <React.Fragment key={record.status}>
        <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>
      </React.Fragment>}
    </FunControlResult></>;
  }
  return <article className={"fun-control-page"+(embedded?" fun-embedded":"")}>
    <GeneratorPageHeader session={embedded ? session : undefined} title="Wan Fun Control 영상 생성"
      description="참조 이미지의 외형과 포즈 영상의 움직임으로 영상을 만듭니다."
      generator="wan22-fun-control-generator" service={service} model={model} onStatus={setModel} embedded={embedded}/>
    <GeneratorSectionNavigation inputRef={formRef} historyRef={historyRef} resultRef={resultRef} inputReady={Boolean(template && request)} resultReady={Boolean(job)} openOnNavigate/>
    {handoffId && <GpuHandoffStatus session={session} id={handoffId} service={service} status={handoffStatus} onUpdate={value=>{setHandoffStatus(value);if(value.job_id)setJob(value.job_id);}}
      onClose={()=>{sessionStorage.removeItem(handoffKey);setHandoffId("");setHandoffStatus(null);}}/>}
    <div ref={activeProgressRef}><ActiveGeneratorProgress service={service} revision={historyRevision+":"+job} onOpenResult={id=>{if(id===job){resultRef.current?.focus();resultRef.current?.scrollIntoView({block:"start"});}else{focusResult.current={id,origin:document.activeElement};setJob(id);}}}/></div>
    {template && request && <form ref={formRef} tabIndex={-1} aria-label="생성 입력" onSubmit={review} onInvalid={event=>{const details=event.target.closest("details");if(details)details.open=true;}}><fieldset disabled={busy || !!pending || Boolean(handoffId)}><legend>생성 입력</legend>
    <fieldset className="fun-source" disabled={busy || !!pending || !template}><legend>원본 작업</legend>
      {loadingInput && <p role="status">입력을 불러오고 있습니다. 현재 입력은 유지됩니다.</p>}
      {sourceJob ? <><p>불러온 원본 작업</p><JobIdentifier id={sourceJob} compact/></> : <p>선택된 원본 작업이 없습니다.</p>}
      {job && <div>{sourceJob!==job && <><p>현재 작업</p><JobIdentifier id={job} compact/></>}<button type="button" disabled={!template} onClick={()=>load(true)}>현재 작업 입력으로 교체</button></div>}
      <details><summary>제작 예제 사용</summary><label>예제 선택<select value={selected} onChange={event=>select(event.target.value)}>
        {template?.examples.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        <button type="button" disabled={!selected} onClick={()=>load()}>선택한 예제로 입력 교체</button></details>
    </fieldset>
      <FunControlFields request={request} setRequest={setRequest} attach={attach} onImageSelectionStart={()=>{attachmentRevision.current++;}} onImageCheckingChange={value=>{imageChecking.current=value;setImageCheckPending(value);}} removePose={()=>{setRequest(current=>({...current,pose_video:""}));setVideoInfo(null);setError(current=>current===poseError?"":current);setPoseError("");}} videoInfo={videoInfo} frameLimit={frameLimit} template={template} sourceSeed={sourceSeed} busy={busy || !!pending || Boolean(handoffId)}/>
      {embedded && <button type="button" onClick={saveDraft}>폼을 대화에 저장</button>}
      <ActionButton type="submit" reasons={[
        imageCheckPending && "선택한 이미지 확인이 끝날 때까지 기다리세요.",
        !request.prompt.trim() && "동작 프롬프트를 입력하세요.",
        !request.images[0] && "외형 참조 이미지를 선택하세요.",
        !request.pose_video && "포즈 영상을 선택하세요."
      ]}>생성 요청 검토</ActionButton>
    </fieldset></form>}
    {pending && <section ref={reviewRef} tabIndex={-1} className="fun-request-review" aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/>
      <p>모델 · {template?.models?.find(item=>item.id===(pending.model_profile || "wan22-14b"))?.label || pending.model_profile || "wan22-14b"}</p>
      <p>외형 참조 이미지 + 포즈 영상 · {pending.frames}프레임 · 16fps · {(pending.frames/16).toFixed(2)}초 · {pending.steps}스텝 · 시드 {pending.seed}</p>
      <p>{videoInfo?.summary || "입력 영상 정보 확인 중"}</p><ReviewPrompt label="동작 프롬프트" text={pending.prompt}/>
      <ReviewPrompt label="부정 프롬프트" text={pending.negative_prompt}/>
      {handoffReview && <p>동의하면 진행 중인 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 영상을 생성합니다. 작업이 끝나면 Qwen 3.8을 다시 GPU에 적재합니다.</p>}
      <GenerationReviewActions disabledReason={modelReason || (handoffId ? "이전 GPU 양도 상태를 먼저 확인하세요." : "")} busy={busy} onCancel={cancelReview} onConfirm={submit} confirmLabel={handoffReview ? "해제·생성·재적재에 동의" : "확인 후 대기열에 추가"}/>
    </section>}
    {error && <p role="alert">{error}</p>}
    {templateError && <p role="alert">{templateError}</p>}
    {restoreError && <div><p role="alert">{restoreError}</p><button ref={restoreRetryRef} type="button" disabled={busy || Boolean(pending)} onClick={()=>{if(restorePending.current || interactionRef.current.busy || interactionRef.current.pending)return;restorePending.current=true;restoreRetryFocus.current=document.activeElement===restoreRetryRef.current;retryRestore(value=>value+1);}}>저장 폼 다시 불러오기</button></div>}
    {seedError && <div><p role="alert">{seedError}</p><button ref={seedRetryRef} type="button" disabled={busy || Boolean(pending)} onClick={()=>{if(seedPending.current || interactionRef.current.busy || interactionRef.current.pending)return;seedPending.current=true;seedRetryFocus.current=document.activeElement===seedRetryRef.current;retrySeed(value=>value+1);}}>원본 입력 다시 불러오기</button></div>}
    {!template && !templateError && <p role="status">생성 입력을 불러오는 중입니다.</p>}
    {!template && templateError && <button ref={templateRetryRef} type="button" onClick={()=>{templateRetryFocus.current=true;retryTemplate(value=>value+1);}}>생성 입력 다시 불러오기</button>}
    {notice && <p role="status">{notice}</p>}
    <fieldset ref={historyRef} className="fun-history" aria-label="작업 이력" disabled={busy || !!pending}>
      <GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id)setJob("");if(sourceJob===id)setSourceJob("");setNotice(message);}} key={historyRevision} service={service} readJobWithSignal={readJob} restore={restore} renderResult={renderResult}/>
      <HistoryCleanup allowSelected={false} service={service} onDeleted={cleaned}/>
    </fieldset>
    {job && <section ref={resultRef} tabIndex={-1} aria-label="현재 작업 결과"><button type="button" onClick={closeResult}>결과 닫기</button>{renderResult(job)}</section>}
  </article>;
}
