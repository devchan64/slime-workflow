import MiniMaxVideoHistoryPage,{miniMaxVideoHistoryUrl} from "./MiniMaxVideoHistoryPage.jsx";
import {useMiniMaxPages,MiniMaxPageNavigation} from "./MiniMaxPageNavigation.jsx";
import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {generationProposalScope,readGenerationProposal} from "./generationProposal.mjs";
import {generationReady} from "./generationReady.mjs";
import {useVideoDelegationReceipt} from "./useVideoDelegationReceipt.js";
import {validVideoJobId} from "./videoJobId.mjs";
import {videoData} from "./videoInputs.js";
import {validRef2vaVideoFile} from "./ref2vaVideoFile.mjs";
import {requestErrorMessage} from "./requestError.mjs";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorUsage from "./GeneratorUsage.jsx";
import {restoreLostFocus,visibleFocusTarget} from "./restoreLostFocus.mjs";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import GeneratorSectionNavigation,{openGeneratorHistory} from "./GeneratorSectionNavigation.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import MiniMaxVideoHistory from "./MiniMaxVideoHistory.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ReviewPrompt from "./ReviewPrompt.jsx";
import ActionButton from "./ActionButton.jsx";
import SeedInput from "./SeedInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import InputVideoPreview from "./InputVideoPreview.jsx";

const service="minimax-h3-ref2va";
export default function MiniMaxH3Ref2VAPage(props={}){
  if(!props.embedded && new URLSearchParams(location.search).has('job'))return <MiniMaxVideoHistoryPage service="minimax-h3-ref2va"/>;
  return <MiniMaxH3Ref2VAPageContent {...props}/>;
}

function MiniMaxH3Ref2VAPageContent({embedded=false,session:embeddedSession=""}={}){
  const {page,navigate}=useMiniMaxPages(!embedded);
  const inputLockId=useId(),videoHelpId=useId(),videoErrorId=useId();
  const session=embeddedSession || new URLSearchParams(location.search).get("session") || "";
  const [prompt,setPrompt]=useState(""),[seed,setSeed]=useState(45),[file,setFile]=useState(null);
  const [model,setModel]=useState(null),[modelError,setModelError]=useState(""),[fileError,setFileError]=useState(""),[error,setError]=useState(""),[notice,setNotice]=useState("");
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[job,setJob]=useState(new URLSearchParams(location.search).get("job") || ""),[revision,setRevision]=useState(0);
  const interactionRef=useRef({busy,pending});interactionRef.current={busy,pending};
  const [proposalScope,setProposalScope]=useState(null);
  const receipt=useVideoDelegationReceipt(proposalScope,service);
  const formRef=useRef(null),inputRef=useRef(null),videoInputRef=useRef(null),historyRef=useRef(null),resultRef=useRef(null),reviewRef=useRef(null),reviewOrigin=useRef(null),sending=useRef(false),editVersion=useRef(0),promptEdited=useRef(false),activeRead=useRef(null);
  useEffect(()=>{if(embedded)return;const id=new URLSearchParams(location.search).get('restore');if(!id)return;const cleanUrl=new URL(location.href);cleanUrl.searchParams.delete('restore');history.replaceState(history.state,'',cleanUrl);if(!validVideoJobId(id)){setError('저장 입력의 작업 ID를 확인할 수 없습니다.');return;}const controller=new AbortController();(async()=>{try{const record=await readSavedInput(id,{signal:controller.signal});if(!controller.signal.aborted)restoreSavedInput(record.request,record);}catch(problem){if(!controller.signal.aborted)setError(problem.message || '저장 입력을 복원할 수 없습니다.');}})();return ()=>controller.abort();},[embedded]);
  useEffect(()=>()=>{const controller=activeRead.current;activeRead.current=null;controller?.abort();},[]);
  useEffect(()=>{let active=true;(async()=>{try{
    const scope=generationProposalScope(location.search,session,'video');if(!scope)return;
    const proposal=await readGenerationProposal(managementCommand,scope);
    if(proposal.service!==service || proposal.mode!=='video_edit' || !proposal.prompt.trim())throw new Error('영상 편집 제안을 확인할 수 없습니다.');
    if(active){setProposalScope(scope);setPrompt(old=>promptEdited.current ? old : old || proposal.prompt);setNotice('대화 제안을 불러왔습니다. 원본 MP4를 선택하고 요청을 검토하세요.');}
  }catch(problem){if(active)setError('대화 제안을 확인할 수 없습니다. '+requestErrorMessage(problem));}})();return()=>{active=false;};},[session]);
  useEffect(()=>{if(receipt.state==='accepted' && receipt.job)setJob(receipt.job);},[receipt.state,receipt.job]);
  useEffect(()=>{if(pending){if(document.activeElement===document.body || document.activeElement===reviewOrigin.current)reviewRef.current?.focus();reviewOrigin.current=null;}},[pending]);
  useEffect(()=>{if(busy || pending || !error || !reviewOrigin.current)return;const origin=reviewOrigin.current;reviewOrigin.current=null;const frame=requestAnimationFrame(()=>restoreLostFocus(document,visibleFocusTarget(origin)));return ()=>cancelAnimationFrame(frame);},[busy,pending,error]);
  const invalidSeed=!Number.isInteger(seed) || seed<0 || seed>2147483647;
  const needsProposal=new URLSearchParams(location.search).has('proposal_job');
  const reasons=[!generationReady(model) && '모델 준비 상태를 확인하세요.',needsProposal && (!proposalScope || receipt.state!=='editing') && '대화 제안의 접수 상태를 확인하세요.',!file && '원본 MP4를 선택하세요.',!prompt.trim() && '편집 프롬프트를 입력하세요.',invalidSeed && '시드는 0~2147483647의 정수여야 합니다.'];
  function choose(event){
    const chosen=event.target.files?.[0];event.target.value="";if(!chosen)return;
    setNotice('');
    if(!validRef2vaVideoFile(chosen)){setFileError('비어 있지 않은 27MiB 이하 MP4를 선택하세요.'+(file ? ' 이전에 선택한 영상은 유지됩니다.' : ''));return;}
    editVersion.current++;setFile(chosen);setFileError("");setError("");
  }
  function removeVideo(event){
    const focused=document.activeElement===event.currentTarget;
    editVersion.current++;setFile(null);setFileError('');setError('');setNotice('원본 영상을 제거했습니다.');
    if(focused)requestAnimationFrame(()=>restoreLostFocus(document,visibleFocusTarget(videoInputRef.current)));
  }
  async function review(event){
    event.preventDefault();if(busy || pending || activeRead.current || reasons.some(Boolean))return;
    reviewOrigin.current=document.activeElement;
    const version=editVersion.current,controller=new AbortController();activeRead.current=controller;setBusy(true);setError("");
    const timer=setTimeout(()=>controller.abort(),30000);
    try{
      const video=await untilAborted(videoData(file),controller.signal);
      if(version!==editVersion.current)throw new Error('입력이 바뀌었습니다. 다시 검토하세요.');
      setPending({action:'generate',prompt:prompt.trim(),images:[],edit_video:video,width:832,height:480,frames:124,steps:8,seed});
    }catch(problem){if(activeRead.current===controller)setError(controller.signal.aborted ? '영상 읽기 시간이 초과됐습니다. 다시 시도하세요.' : problem.message || '영상을 읽을 수 없습니다.');}
    finally{clearTimeout(timer);if(activeRead.current===controller){activeRead.current=null;setBusy(false);}}
  }
  useEffect(()=>{if(embedded)return;const syncJob=()=>{const id=new URLSearchParams(location.search).get("job");setJob(id || "");};window.addEventListener("popstate",syncJob);return ()=>window.removeEventListener("popstate",syncJob);},[embedded]);
  useEffect(()=>{if(!embedded && page==="history"){const details=historyRef.current?.querySelector('details.generator-history');if(details)details.open=true;}},[embedded,page]);
  async function submit(){
    if(!pending || sending.current || !generationReady(model) || (proposalScope && receipt.state!=='editing'))return;
    sending.current=true;setBusy(true);setError("");setNotice("");
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),120000);
    try{
      if(proposalScope)await readGenerationProposal(managementCommand,proposalScope,{signal:controller.signal});
      const result=await untilAborted(proposalScope ? managementCommand('hermes-agent','hermes-delegate-video',{request_id:receipt.id,service,request:pending},{signal:controller.signal}) : managementCommand(service,'generate',pending,{signal:controller.signal}),controller.signal);
      const resultId=proposalScope ? (result?.state==='accepted' ? result.job_id : null) : result?.id;
      if(!validVideoJobId(resultId))throw new Error('접수 ID를 확인할 수 없습니다.');
      if(proposalScope)receipt.refresh();
      setJob(resultId);setRevision(value=>value+1);setNotice('편집 요청을 접수했습니다. 이력에서 진행 상태를 확인하세요.');
    }catch(problem){if(proposalScope)receipt.unknown();setError((controller.signal.aborted ? '접수 응답 시간이 초과됐습니다.' : requestErrorMessage(problem))+' · 재접수 전에 이력과 접수 상태를 확인하세요.');}
    finally{const restore=reviewRef.current?.contains(document.activeElement);clearTimeout(timer);sending.current=false;setBusy(false);setPending(null);if(restore)requestAnimationFrame(()=>restoreLostFocus(document,visibleFocusTarget(formRef.current)));}
  }
  function cancelReview(){
    const restore=reviewRef.current?.contains(document.activeElement);setPending(null);
    if(restore)requestAnimationFrame(()=>restoreLostFocus(document,visibleFocusTarget(formRef.current)));
  }
  async function readSavedInput(id,{signal}={}){
    const version=editVersion.current,focusAtStart=document.activeElement;
    const response=await untilAborted(fetch('/management/assistant/minimax-h3-ref2va-input/'+encodeURIComponent(id),{cache:'no-store',signal}),signal);
    if(!response.ok)throw new Error('저장된 입력 또는 원본 영상 사본을 확인할 수 없습니다.');
    let record;try{record=await untilAborted(response.json(),signal);}catch(problem){signal?.throwIfAborted();throw new Error('저장 입력 형식을 확인할 수 없습니다. 다시 조회하세요.');}const request=record?.request;
    if(record?.id!==id || !request || request.action!=='generate' || typeof request.prompt!=='string' || !request.prompt.trim() || typeof request.edit_video!=='string' || request.width!==832 || request.height!==480 || request.frames!==124 || request.steps!==8 || !Number.isInteger(request.seed) || request.seed<0 || request.seed>2147483647)throw new Error('저장 입력 형식을 확인할 수 없습니다.');
    return {...record,version,focusAtStart};
  }
  function restoreSavedInput(request,record){
    if(busy || pending || activeRead.current || editVersion.current!==record.version)throw new Error('조회 중 입력이 바뀌어 적용하지 않았습니다. 다시 시도하세요.');
    const decoded=atob(request.edit_video),bytes=new Uint8Array(decoded.length);
    for(let index=0;index<decoded.length;index++)bytes[index]=decoded.charCodeAt(index);
    if(!embedded)navigate("input");
    editVersion.current++;promptEdited.current=true;setPrompt(request.prompt);setSeed(request.seed);setFile(new File([bytes],'edit-video.mp4',{type:'video/mp4'}));setFileError('');setError('');setNotice(record.id+'의 입력을 적용했습니다.');
    if(inputRef.current)inputRef.current.open=true;
    const appliedVersion=editVersion.current;requestAnimationFrame(()=>{if(editVersion.current===appliedVersion && !activeRead.current && !interactionRef.current.busy && !interactionRef.current.pending && (document.activeElement===document.body || document.activeElement===record.focusAtStart) && formRef.current?.isConnected)formRef.current.focus();});
  }
  return <article className={'vace-page generator-page-common'+(embedded ? '' : ' vace-standalone')}>
    <GeneratorPageIdentity service={service} embedded={embedded} session={session} changelogCard/>
    <GeneratorUsage generator={service}/>
    {needsProposal && <div><p role="status">{receipt.state==='accepted' ? '접수된 작업 '+receipt.job+' · 결과는 생성기 이력에서 확인하세요.' : receipt.state==='editing' ? '대화 제안을 확인했습니다.' : receipt.state==='checking' ? '접수 상태를 확인하고 있습니다.' : '접수 여부를 확인하세요.'}</p><button type="button" onClick={receipt.refresh}>접수 상태 새로고침</button></div>}
    {!embedded ? <MiniMaxPageNavigation page={page} navigate={(next,id)=>next==="history" ? window.open(miniMaxVideoHistoryUrl(service,id,session),"_blank","noopener") : navigate(next,id)} locked={busy || !!pending}/> : <GeneratorSectionNavigation inputRef={formRef} historyRef={historyRef} resultRef={resultRef} resultReady={Boolean(job)} openOnNavigate/>}
    <GeneratorSectionCard title="모델 준비" summary={modelError ? '상태 조회 실패' : !model ? '상태 확인 중' : generationReady(model) ? '준비 완료' : '준비 필요'}><ModelReadiness service={service} session={session} onStatus={setModel} onError={setModelError}/></GeneratorSectionCard>
    <ActiveGeneratorProgress service={service} revision={revision+':'+job} onOpenResult={id=>{if(!embedded)window.open(miniMaxVideoHistoryUrl(service,id,session),"_blank","noopener");else openGeneratorHistory(historyRef,id,setJob);}}/>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}{!embedded && <p>생성이력은 새 탭에서 열려 현재 입력을 유지합니다. {validVideoJobId(job) && <a href={miniMaxVideoHistoryUrl(service,job,session)} target="_blank" rel="noopener">작업 이력 보기</a>}</p>}
    <div hidden={!embedded && page!=="input"}><GeneratorSectionCard title="편집 입력" summary={fileError ? "원본 영상 확인 실패" : "원본 영상과 편집 지시"} defaultOpen cardRef={inputRef} className="vace-input-card"><form ref={formRef} tabIndex={-1} onSubmit={review}><fieldset disabled={busy || !!pending} aria-describedby={busy || pending ? inputLockId : undefined}>
      <legend className="generator-visually-hidden">영상 편집 입력</legend>
      <label>원본 MP4<input ref={videoInputRef} type="file" accept="video/mp4" aria-invalid={Boolean(fileError)} aria-describedby={[videoHelpId,fileError && videoErrorId].filter(Boolean).join(" ")} onChange={choose}/></label>
      <p id={videoHelpId}>{'832×480 · 24fps · 정확히 124프레임 · 최대 27MiB'+(file ? ' · 선택: '+file.name : '')+'. 입력 조건은 접수 시 검증합니다.'}</p>
      {fileError && <p id={videoErrorId} role="alert">{fileError}</p>}
      {file && <button type="button" onClick={removeVideo}>원본 영상 제거</button>}
      <InputVideoPreview file={file} label="원본 영상"/>
      <label>편집 프롬프트<textarea required maxLength={8000} value={prompt} onChange={event=>{editVersion.current++;promptEdited.current=true;setPrompt(event.target.value);}}/></label><PromptWordCount text={prompt} final/>
      <SeedInput value={seed} max={2147483647} error={invalidSeed ? '0~2147483647의 정수를 입력하세요.' : ''} onChange={value=>{editVersion.current++;setSeed(value===''?'':Number(value));}}/>
      <p>출력 832×480 · 124프레임 · 24fps · Turbo 8스텝. 원본 오디오는 유지되지 않습니다.</p>
      <ActionButton type="submit" reasons={reasons}>편집 요청 검토</ActionButton>
    </fieldset>{(busy || pending) && <p id={inputLockId} role="status">{busy ? "요청을 처리하고 있습니다. 잠시 기다려 주세요." : "입력을 수정하려면 편집 요청 검토에서 입력 수정을 선택하세요."}</p>}</form></GeneratorSectionCard>
    {pending && <section ref={reviewRef} tabIndex={-1} className="fun-request-review" aria-label="편집 요청 확인"><h2>편집 요청 확인</h2><GpuQueueSummary/><p>{file?.name} · 832×480 · 124프레임 · 24fps · 8스텝 · 시드 {pending.seed}</p><ReviewPrompt label="편집 프롬프트" text={pending.prompt}/><GenerationReviewActions busy={busy} disabledReason={!generationReady(model) ? '모델 준비 상태를 확인하세요.' : ''} onCancel={cancelReview} onConfirm={submit}/></section>}
    </div>
    {(embedded || page==="history") && <MiniMaxVideoHistory service={service} job={job} setJob={setJob} revision={revision} setRevision={setRevision} readJob={readSavedInput} restore={restoreSavedInput} historyRef={historyRef} resultRef={resultRef} onNotice={setNotice} resultLabel="선택한 영상 편집 결과"/>}
  </article>;
}
