import React, {useCallback, useEffect, useId, useRef, useState} from "react";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorUsage from "./GeneratorUsage.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import MiniMaxImageHistoryPage, {MiniMaxImageHistory,minimaxImageHistoryUrl} from "./MiniMaxImageHistoryPage.jsx";
import SeedInput from "./SeedInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ActionButton from "./ActionButton.jsx";
import GeneratorSectionNavigation,{openGeneratorHistory} from "./GeneratorSectionNavigation.jsx";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {restoreLostFocus,visibleFocusTarget} from "./restoreLostFocus.mjs";
import {useMinimaxReportReceipt,MinimaxReportStatus} from "./useMinimaxReportReceipt.jsx";
import {verifyFluxProposal} from "./fluxProposalReceipt.mjs";
import {validGenerationJobId} from "./generationJobId.mjs";
import {requestErrorMessage} from "./requestError.mjs";
import ReferenceImageInput, {verifyReferenceImage} from "./ReferenceImageInput.jsx";
import {referenceImageError} from "./referenceImageValidation.mjs";
import CardGallery from "./CardGallery.jsx";
import {useMiniMaxPages,MiniMaxPageNavigation} from "./MiniMaxPageNavigation.jsx";
import {filterFluxGuides} from "./fluxGuides.mjs";

const service = "minimax-h3-image";
export function minimaxImageReasons({model,prompt,seed}) {
  return [!model?.generation_ready && "모델 준비 상태를 확인하세요.",!prompt.trim() && "프롬프트를 입력하세요.",(!Number.isInteger(seed) || seed<0 || seed>4294967295) && "시드는 0부터 4294967295까지의 정수로 입력하세요."];
}
function imageBase64(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('참조 이미지를 읽을 수 없습니다.'));reader.readAsDataURL(file);});}
export default function MiniMaxH3ImagePage(props={}) {
  const q=new URLSearchParams(location.search);
  if(!props.embedded && (q.get('view')==='history' || validGenerationJobId(q.get('job'))))return <MiniMaxImageHistoryPage building={props.building}/>;
  return <MiniMaxH3ImageForm {...props}/>;
}
function MiniMaxH3ImageForm({embedded=false,session:embeddedSession="",initialInputs=null,proposalScope=null,reportReceipt=null,building=false}={}) {
  const separatePages=!embedded;
  const {page,navigate}=useMiniMaxPages(false);
  const navigationPending=useRef(false);
  async function navigatePage(next,id){
    if(separatePages && next==='history'){
      if(navigationPending.current)return;
      if(checkingSlots.current.size){setError('참조 이미지 확인이 끝난 뒤 이력을 열어 주세요.');return;}
      navigationPending.current=true;const version=inputRevision.current;
      try{
        const images=await Promise.all(references.map(file=>file ? imageBase64(file) : null));
        if(version!==inputRevision.current || checkingSlots.current.size){setError('입력 보존 중 내용이 변경되어 이동하지 않았습니다. 다시 시도하세요.');return;}
        sessionStorage.setItem('minimax-image-draft-'+(building?'building':'general'),JSON.stringify({prompt,seed,size,downscale,sampler,images}));
        location.assign(minimaxImageHistoryUrl(building,id,session));
      }catch{setError('현재 입력을 보존하지 못해 이력으로 이동하지 않았습니다. 저장 공간을 확인하세요.');}
      finally{navigationPending.current=false;}
      return;
    }
    navigate(next,id);if(id)setJob(id);
  }
  const session=embeddedSession || new URLSearchParams(window.location.search).get("session") || "";
  const inputLockId=useId(),secondReferenceId=useId(),samplerHintId=useId();
  const [prompt,setPrompt]=useState(initialInputs?.prompt || (building ? "완전한 판타지 건물 스프라이트 하나. <Picture 1>의 직교 아이소메트릭 바닥 범위, 평행한 타일 축, 수직선과 출입구를 따른다. 일정한 크기, 왼쪽 위에서 비치는 부드러운 조명, 단색 배경. 가이드와 지형은 그리지 않는다. 건물 디자인: " : "")), [seed,setSeed]=useState(initialInputs?.seed ?? 42), [model,setModel]=useState(null), [modelError,setModelError]=useState("");
  const [size,setSize]=useState(initialInputs?.width===832 && initialInputs?.height===480 ? 832 : initialInputs?.width===512 && initialInputs?.height===512 ? 512 : 1024);
  const [downscale,setDownscale]=useState(false), [sampler,setSampler]=useState("lcm");
  const [notice,setNotice]=useState("");
  const [guides,setGuides]=useState([]),[guide,setGuide]=useState(""),[guideError,setGuideError]=useState("");
  const [guideListError,setGuideListError]=useState(""),[guideLoading,setGuideLoading]=useState(building),[guideAttempt,setGuideAttempt]=useState(0);
  const guideHeadingRef=useRef(null);
  useEffect(()=>{
    if(!building)return;
    let active=true,timedOut=false;const controller=new AbortController();
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setGuideLoading(true);setGuideListError("");
    untilAborted((async()=>{const response=await fetch("/management/assistant/flux-defaults/flux-building",{signal:controller.signal});if(!response.ok)throw Error();return await response.json();})(),controller.signal)
      .then(data=>{if(!Array.isArray(data?.guides) || data.guides.some(item=>!item || typeof item.id!=="string" || !item.id.trim() || typeof item.label!=="string" || !item.label.trim()) || new Set(data.guides.map(item=>item.id)).size!==data.guides.length)throw Error();if(active)setGuides(data.guides);})
      .catch(()=>{if(active && (!controller.signal.aborted || timedOut))setGuideListError(timedOut ? "건물 가이드 조회 시간이 초과됐습니다." : "건물 가이드 목록을 불러오지 못했습니다.");})
      .finally(()=>{clearTimeout(timeout);if(active)setGuideLoading(false);});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[building,guideAttempt]);
  async function applyBuildingGuide(event){
    if(!guide || busy || pending || checking.some(Boolean) || guideRequest.current)return;
    guideApplyFocus.current=document.activeElement===event.currentTarget ? event.currentTarget : null;
    const version=++inputRevision.current,controller=new AbortController();guideRequest.current=controller;
    let timedOut=false;const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setGuideError("");setNotice("");
    try{
      const blob=await untilAborted((async()=>{const response=await fetch("/management/assistant/flux-building-guide/"+encodeURIComponent(guide),{signal:controller.signal});if(!response.ok)throw Error();return await response.blob();})(),controller.signal);
      if(guideRequest.current!==controller || controller.signal.aborted)return;
      if(referenceImageError(blob,"image/png",3000000))throw Error();
      await untilAborted(verifyReferenceImage(blob,"image/png"),controller.signal);
      if(guideRequest.current!==controller || controller.signal.aborted)return;
      if(inputRevision.current!==version)throw Error();
      setReferences(current=>[new File([blob],guide+".png",{type:"image/png"}),current[1]]);setReferenceReset(value=>value+1);setNotice("선택한 가이드를 첫 번째 참조에 적용했습니다.");
    }catch{if(guideRequest.current===controller && (!controller.signal.aborted || timedOut))setGuideError((timedOut ? "가이드 적용 시간이 초과됐습니다. 다시 시도하세요." : "가이드를 적용하지 못했습니다. 다시 시도하세요.")+(references[0] ? " 기존 참조는 유지됩니다." : ""));}
    finally{clearTimeout(timeout);if(guideRequest.current===controller){guideRequest.current=null;setBusy(false);}}
  }
  const inputRevision=useRef(0),checkingSlots=useRef(new Set()),interaction=useRef(null);
  const [references,setReferences]=useState([null,null]),[checking,setChecking]=useState([false,false]),[referenceErrors,setReferenceErrors]=useState([false,false]),[previewErrors,setPreviewErrors]=useState([false,false]),[referenceReset,setReferenceReset]=useState(0);
  const [pending,setPending]=useState(null), [preview,setPreview]=useState(""), [busy,setBusy]=useState(false), [error,setError]=useState("");
  const [job,setJob]=useState(()=>{
    const linked=new URLSearchParams(window.location.search).get("job");
    return !embedded && validGenerationJobId(linked) ? linked : "";
  }), [revision,setRevision]=useState(0);
  const localReceipt=useMinimaxReportReceipt(reportReceipt ? null : proposalScope,service);
  const receipt=reportReceipt || localReceipt;
  interaction.current={busy,pending,receiptState:receipt.state};
  useEffect(()=>{if(receipt.state==="accepted" && receipt.job)setJob(receipt.job);},[receipt.state,receipt.job]);
  const invalidSeed=!Number.isInteger(seed) || seed<0 || seed>4294967295;
  const reasons=[...minimaxImageReasons({model,prompt,seed}),checking.some(Boolean) && "참조 이미지 확인이 끝날 때까지 기다리세요.",building && !references[0] && "건물 배치 가이드 또는 첫 번째 참조 이미지를 선택하세요.",proposalScope && receipt.state!=="editing" && "대화 접수 상태를 확인하세요."];
  const sending=useRef(false),promptRef=useRef(null),reviewRef=useRef(null),formRef=useRef(null),historyRef=useRef(null),resultRef=useRef(null),previewRequest=useRef(null),submissionRequest=useRef(null),modelStatus=useRef(null),previewFocus=useRef(null),guideApplyFocus=useRef(null),guideRequest=useRef(null);
  const updateModel=useCallback(value=>{modelStatus.current=value;setModel(value);},[]);
  useEffect(()=>()=>{const preview=previewRequest.current,submission=submissionRequest.current,guide=guideRequest.current;previewRequest.current=null;submissionRequest.current=null;guideRequest.current=null;preview?.abort();submission?.abort();guide?.abort();},[]);
  useEffect(()=>{if(pending && previewFocus.current && (document.activeElement===previewFocus.current || document.activeElement===document.body))reviewRef.current?.focus();},[pending]);
  useEffect(()=>{if(!busy && previewFocus.current){if(error)restoreLostFocus(document,previewFocus.current);previewFocus.current=null;}},[busy,error]);
  useEffect(()=>{if(!busy && guideApplyFocus.current){restoreLostFocus(document,visibleFocusTarget(guideApplyFocus.current));guideApplyFocus.current=null;}},[busy]);
  useEffect(()=>{if(embedded)return;const parameters=new URLSearchParams(location.search);if(!parameters.has('restore'))return;const id=parameters.get('restore');if(!validGenerationJobId(id)){const url=new URL(location.href);url.searchParams.delete('restore');history.replaceState(history.state,'',url);setError('저장 입력의 작업 ID를 확인할 수 없습니다.');return;}const controller=new AbortController();readSavedInput(id,{signal:controller.signal}).then(record=>{if(!controller.signal.aborted){restoreSavedInput(record.request,record);const url=new URL(location.href);url.searchParams.delete('restore');history.replaceState(history.state,'',url);}}).catch(problem=>{if(!controller.signal.aborted)setError(problem.message || '저장 입력을 적용하지 못했습니다.');});return ()=>controller.abort();},[embedded]);
  useEffect(()=>{if(embedded || new URLSearchParams(location.search).has('restore'))return;const key='minimax-image-draft-'+(building?'building':'general');try{const raw=sessionStorage.getItem(key);if(!raw)return;const draft=JSON.parse(raw);if(typeof draft.prompt!=='string' || !Array.isArray(draft.images) || draft.images.length!==2)throw Error();const files=draft.images.map((value,index)=>{if(!value)return null;return new File([Uint8Array.from(atob(value),c=>c.charCodeAt(0))],`reference-${index+1}.png`,{type:'image/png'});});setPrompt(draft.prompt);setSeed(draft.seed);setSize(draft.size);setDownscale(draft.downscale);setSampler(draft.sampler);setReferences(files);setReferenceReset(n=>n+1);setNotice('이력으로 이동하기 전 입력을 복원했습니다.');sessionStorage.removeItem(key);}catch{setError('이전 입력을 복원하지 못했습니다.');}},[embedded,building]);
  async function review(event){
    event.preventDefault();
    if((proposalScope && receipt.state!=="editing") || sending.current || busy || pending || checking.some(Boolean) || (building && !references[0]) || !model?.generation_ready || !prompt.trim() || !Number.isInteger(seed) || seed<0 || seed>4294967295)return;
    inputRevision.current++;
    const focused=document.activeElement;previewFocus.current=focused;
    sending.current=true;setBusy(true);setError("");
    const height=size===832?480:size;
    const request={action:"generate",prompt:prompt.trim(),images:[],width:downscale?size*2:size,height:downscale?height*2:height,steps:6,seed,...(!proposalScope?{sampler}:{}),...(downscale?{output_size:{width:size,height}}:{})};
    const controller=new AbortController();previewRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      request.images=await Promise.all(references.filter(Boolean).map(imageBase64));
      if(controller.signal.aborted)return;
      if(proposalScope)await untilAborted(verifyFluxProposal(managementCommand,proposalScope,proposalScope.proposal),controller.signal);
      const result=await untilAborted(managementCommand(service,"preview",request,{signal:controller.signal}),controller.signal);
      if(previewRequest.current!==controller)return;
      if(typeof result?.prompt!=="string" || !result.prompt || !/^[a-f0-9]{64}$/.test(result?.prompt_sha256 || ""))throw new Error("최종 프롬프트를 확인할 수 없습니다.");
      setPreview(result.prompt);setPending({...request,expected_prompt_sha256:result.prompt_sha256});
    }catch(problem){if(previewRequest.current===controller)setError(timedOut ? "프롬프트 검토 시간이 초과됐습니다. 다시 시도하세요." : requestErrorMessage(problem));}
    finally{clearTimeout(timeout);if(previewRequest.current===controller){previewRequest.current=null;sending.current=false;setBusy(false);}}
  }
  async function readSavedInput(id,{signal}={}){
    const revisionAtStart=inputRevision.current,checkingAtStart=checkingSlots.current.size>0,focusAtStart=document.activeElement;
    const controller=new AbortController();let timedOut=false;
    const cancel=()=>controller.abort();
    if(signal?.aborted)controller.abort();else signal?.addEventListener('abort',cancel,{once:true});
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      const response=await untilAborted(fetch('/management/assistant/minimax-h3-image-input/'+encodeURIComponent(id),{signal:controller.signal,cache:'no-store'}),controller.signal);
      if(!response.ok)throw new Error('저장된 입력을 읽을 수 없습니다.');
      let record;
      try{record=await untilAborted(response.json(),controller.signal);}
      catch(problem){if(controller.signal.aborted)throw problem;throw new Error('저장 입력 응답을 확인할 수 없습니다. 다시 시도하세요.');}
      const request=record?.request;
      if(record?.id!==id || !request || typeof request!=='object' || Array.isArray(request) || !Array.isArray(request.images) || request.images.length>2 || request.images.some(image=>typeof image!=='string'))throw new Error('선택한 작업의 저장 입력을 확인할 수 없습니다.');
      const output=request?.output_size || {width:request?.width,height:request?.height},scaled=request?.output_size!=null;
      const supported=(output.width===832 && output.height===480)||(output.width===512 && output.height===512)||(output.width===1024 && output.height===1024);
      if(request.action!=='generate' || typeof request.prompt!=='string' || !request.prompt.trim() || request.prompt.length>8000 || !Number.isInteger(request.seed) || request.seed<0 || request.seed>4294967295 || request.steps!==6 || !['euler','lcm'].includes(request.sampler ?? 'euler') || !supported || request.width!==output.width*(scaled?2:1) || request.height!==output.height*(scaled?2:1))throw new Error('현재 화면에서 지원하지 않는 저장 설정이 있어 적용하지 않았습니다.');
      const files=request.images.map((image,index)=>{let bytes;try{bytes=Uint8Array.from(atob(image),character=>character.charCodeAt(0));}catch{throw new Error('저장된 참조 이미지를 확인할 수 없습니다.');}if(!bytes.length)throw new Error('저장된 참조 이미지를 확인할 수 없습니다.');return new File([bytes],`reference-${index+1}.png`,{type:'image/png'});});
      return {id,request,files,revisionAtStart,checkingAtStart,focusAtStart,output,scaled};
    }catch(problem){if(timedOut)throw new Error('저장 입력 조회 시간이 초과됐습니다. 다시 시도하세요.');throw problem;}
    finally{clearTimeout(timer);signal?.removeEventListener('abort',cancel);}
  }
  function restoreSavedInput(request,record){
    const current=interaction.current;
    if(record.checkingAtStart || checkingSlots.current.size || inputRevision.current!==record.revisionAtStart || current.busy || current.pending || sending.current || (proposalScope && current.receiptState!=='editing'))throw new Error('입력 확인 중이거나 조회 중 입력 또는 생성 상태가 바뀌어 적용하지 않았습니다. 확인 후 다시 시도하세요.');
    if(proposalScope && (record.scaled || (request.sampler ?? 'euler')!=='lcm'))throw new Error('이 대화 제안에는 LCM 샘플러와 축소 없는 입력만 적용할 수 있습니다. 다른 이력을 선택하세요.');

    const revision=++inputRevision.current;setPrompt(request.prompt);setSeed(request.seed);setSize(record.output.width);setDownscale(record.scaled);setSampler(request.sampler ?? "euler");setReferences([record.files[0] || null,record.files[1] || null]);setReferenceReset(value=>value+1);setError('');setNotice(record.id+'의 입력을 적용했습니다.');
    const card=formRef.current?.closest('details');if(card)card.open=true;
    requestAnimationFrame(()=>{if(inputRevision.current===revision && !interaction.current.busy && !interaction.current.pending && (document.activeElement===document.body || document.activeElement===record.focusAtStart))visibleFocusTarget(formRef.current)?.focus();});
  }
  function closeReview(){
    const restore=reviewRef.current?.contains(document.activeElement);
    setPending(null);setPreview("");
    if(restore)requestAnimationFrame(()=>restoreLostFocus(document,visibleFocusTarget(promptRef.current)));
  }
  useEffect(()=>{if(embedded)return;const syncJob=()=>{const id=new URLSearchParams(location.search).get("job");setJob(id || "");};window.addEventListener("popstate",syncJob);return ()=>window.removeEventListener("popstate",syncJob);},[embedded]);
  useEffect(()=>{if(!embedded && page==="history"){const details=historyRef.current?.querySelector('details.generator-history');if(details)details.open=true;}},[embedded,page]);
  async function submit(){
    if(!pending || sending.current || !modelStatus.current?.generation_ready || (proposalScope && receipt.state!=="editing"))return;
    sending.current=true;setBusy(true);setError("");
    const controller=new AbortController();submissionRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
      if(proposalScope)await untilAborted(verifyFluxProposal(managementCommand,proposalScope,proposalScope.proposal),controller.signal);
      const result=await untilAborted(proposalScope ? managementCommand("hermes-agent","hermes-minimax-submit",{session_id:proposalScope.session,proposal_job_id:proposalScope.job,request_id:receipt.id,service,request:pending},{signal:controller.signal}) : managementCommand(service,"generate",pending,{signal:controller.signal}),controller.signal);
      if(submissionRequest.current!==controller)return;
      const resultId=proposalScope ? (result?.state==="accepted" ? result.job_id : null) : result?.id;
      if(!validGenerationJobId(resultId))throw new Error("접수 ID를 확인할 수 없습니다.");
      if(proposalScope)receipt.refresh();
      setJob(resultId);setRevision(n=>n+1);setPending(null);if(separatePages)navigatePage("history",resultId);
    }catch(problem){if(proposalScope)receipt.unknown();if(submissionRequest.current===controller)setError((timedOut ? "응답 시간이 초과됐습니다." : problem?.message ? requestErrorMessage(problem) : "응답을 확인할 수 없습니다.")+" 접수 여부가 불확실합니다. 재접수 전에 이력을 확인하세요.");}
    finally{clearTimeout(timeout);if(submissionRequest.current===controller){submissionRequest.current=null;sending.current=false;setBusy(false);}}
  }
  return <article className={"vace-page generator-page-common"+(embedded ? "" : " vace-standalone")}>
    <GeneratorPageIdentity service={building ? "minimax-h3-building" : service} embedded={embedded} session={session} changelogCard/>
    <GeneratorUsage generator={building ? "minimax-h3-building" : service}/>{building && <p>일반 MiniMax 이미지 생성기와 모델, 대기열 및 전체 이력을 공유합니다. 프롬프트는 입력한 그대로 전달하며 별도의 번역 기능을 사용하지 않습니다.</p>}{separatePages && <p>이력 페이지 이동 전 입력은 이 브라우저 탭에 임시 보존됩니다. 저장된 작업은 이력에서 입력을 다시 적용할 수 있습니다.</p>}
    {proposalScope && !reportReceipt && <MinimaxReportStatus receipt={receipt}/>}
    {separatePages ? <MiniMaxPageNavigation page={page} navigate={navigatePage} locked={busy || !!pending} reviewHref={building ? "/management/frame/building-editor/" : undefined}/> : <GeneratorSectionNavigation inputRef={formRef} historyRef={historyRef} resultRef={resultRef} resultReady={Boolean(job)} openOnNavigate/>}
    <GeneratorSectionCard title="모델 준비" summary={modelError ? "상태 조회 실패" : !model ? "상태 확인 중" : model.generation_ready ? "준비 완료" : "준비 필요"}><ModelReadiness service={service} session={session} onStatus={updateModel} onError={setModelError}/></GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={revision} onOpenResult={id=>separatePages ? navigatePage("history",id) : openGeneratorHistory(historyRef,id,setJob)}/>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <div hidden={separatePages && page!=="input"}><GeneratorSectionCard title="생성 입력" summary={[checking.some(Boolean) && "참조 이미지 확인 중",referenceErrors.some(Boolean) && "참조 이미지 확인 실패",previewErrors.some(Boolean) && "참조 미리보기 실패"].filter(Boolean).join(" · ") || "프롬프트와 시드"} defaultOpen className="vace-input-card"><form ref={formRef} tabIndex={-1} aria-label="생성 입력" onChangeCapture={()=>{inputRevision.current++;setNotice("");}} onSubmit={review}><fieldset disabled={busy || !!pending} aria-describedby={busy || pending ? inputLockId : undefined}><legend className="generator-visually-hidden">생성 입력</legend>
      {building && <section className="flux-guides"><h2 ref={guideHeadingRef} tabIndex={-1}>건물 배치 가이드</h2>{guideLoading && <p role="status">건물 가이드 목록을 불러오는 중입니다.</p>}{guideListError && <div role="alert"><p>{guideListError} 직접 참조 PNG를 선택할 수도 있습니다.</p><button type="button" onClick={event=>{if(document.activeElement===event.currentTarget)guideHeadingRef.current?.focus();setGuideAttempt(value=>value+1);}}>가이드 목록 다시 불러오기</button></div>}{!guideLoading && !guideListError && <CardGallery items={guides} selected={guide} onSelect={setGuide} label="가이드" matches={(item,query)=>filterFluxGuides([item],query).length>0} imageUrl={item=>"/management/assistant/flux-building-guide/"+encodeURIComponent(item.id)+"?thumbnail=true"}/>}<ActionButton type="button" reasons={[!guide && "가이드를 선택하세요.",checking.some(Boolean) && "참조 이미지 확인이 끝날 때까지 기다리세요."]} onClick={applyBuildingGuide}>선택한 가이드를 첫 참조에 적용</ActionButton>{guideError && <p role="alert">{guideError}</p>}</section>}
      <label>{building ? "건물 디자인 및 프롬프트" : "프롬프트"}<textarea ref={promptRef} required maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <PromptWordCount text={prompt}/>
      <SeedInput value={seed} max={4294967295} error={invalidSeed ? "0부터 4,294,967,295까지의 정수로 입력하세요." : ""} onChange={value=>{inputRevision.current++;setNotice("");setSeed(value===""?"":Number(value));}}/>
      <label>이미지 크기<select value={size} onChange={event=>{inputRevision.current++;setNotice("");setSize(Number(event.target.value));}}><option value={832}>832×480</option><option value={512}>512×512</option><option value={1024}>1024×1024</option></select></label>
      {!proposalScope && <label>샘플러<select aria-describedby={sampler==="lcm" ? samplerHintId : undefined} value={sampler} onChange={event=>{inputRevision.current++;setNotice("");setSampler(event.target.value);}}><option value="lcm">LCM · 기본 · 실험</option><option value="euler">Euler</option></select></label>}
      {!proposalScope && sampler==="lcm" && <p id={samplerHintId}>LCM은 실험 기능입니다. 시드에 따른 재현성과 화풍·캐릭터 유지 품질은 검수 중입니다.</p>}
      {!proposalScope && <label><input type="checkbox" checked={downscale} onChange={event=>{inputRevision.current++;setNotice("");setDownscale(event.target.checked);}}/> 2배 크기로 생성 후 축소</label>}
      {downscale && <p>생성 {size*2}×{(size===832?480:size)*2} · 최종 {size}×{size===832?480:size} · OpenCV 영역 보간</p>}
      <section aria-label="참조 이미지"><p>참조 PNG · 최대 2장</p><div className="reference-image-slots">{[0,1].map(index=><ReferenceImageInput key={index===1 ? "second-"+Boolean(references[0]) : "first"} resetErrorKey={referenceReset} label={"참조 이미지 "+(index+1)} accept="image/png" maxBytes={3000000} source={references[index]} disabled={busy || !!pending || (index===1 && !references[0])} describedBy={index===1 && !references[0] ? secondReferenceId : undefined} onSelectionStart={()=>{inputRevision.current++;setNotice("");}} onPreviewErrorChange={value=>setPreviewErrors(previous=>{const next=[...previous];next[index]=value;return next;})} onErrorChange={value=>setReferenceErrors(previous=>{const next=[...previous];next[index]=value;return next;})} onCheckingChange={value=>{if(value)checkingSlots.current.add(index);else checkingSlots.current.delete(index);setChecking(previous=>{const next=[...previous];next[index]=value;return next;});}} onChange={value=>{inputRevision.current++;setNotice("");setReferences(previous=>{const next=[...previous];next[index]=value;if(index===0 && !value)next[1]=null;return next;});}}/>)}</div>{!references[0] && <p id={secondReferenceId}>두 번째 참조를 추가하려면 먼저 첫 번째 참조를 선택하세요.</p>}</section>
      <p>직접 생성 · 6스텝 · INT8{size===512 && " · 512×512 실제 생성 미검증"}</p>
      <ActionButton type="submit" reasons={reasons}>생성 요청 검토</ActionButton>
    </fieldset>{(busy || pending) && <p id={inputLockId} role="status">{pending ? "입력을 수정하려면 아래 검토에서 입력 수정을 선택하세요." : "최종 프롬프트를 확인하고 있습니다. 잠시 기다려 주세요."}</p>}</form></GeneratorSectionCard>
    {pending && <section ref={reviewRef} tabIndex={-1} className="fun-request-review minimax-image-review" aria-label="생성 요청 확인"><h2>공용 화풍 적용 프롬프트</h2><GpuQueueSummary/><pre className="generation-review-text" tabIndex={0} aria-label="검토할 프롬프트">{preview}</pre><PromptWordCount text={preview} label="최종 프롬프트"/><p>생성 {pending.width}×{pending.height}{pending.output_size && ` · 최종 ${pending.output_size.width}×${pending.output_size.height} (OpenCV)`} · 6스텝 · {(pending.sampler ?? "lcm") === "lcm" ? "LCM · 기본 · 실험" : "Euler"} · 시드 {pending.seed} · 참조 {pending.images.length}장</p><GenerationReviewActions busy={busy} disabledReason={!model?.generation_ready ? "모델 준비 상태를 확인하세요." : proposalScope && receipt.state!=="editing" ? "대화 접수 상태를 확인하세요." : ""} onCancel={closeReview} onConfirm={submit}/></section>}
    </div>
    {!separatePages && <MiniMaxImageHistory job={job} setJob={setJob} revision={revision} setRevision={setRevision} readJob={readSavedInput} restore={restoreSavedInput} historyRef={historyRef} resultRef={resultRef}/>}
  </article>;
}
