import {audioInputIssues} from "./audioInputIssues.mjs";
import {createConfirmationGate} from "./confirmationGate.mjs";
import {generationReady} from "./generationReady.mjs";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import useGpuHandoff from "./useGpuHandoff.js";
import ActionButton from "./ActionButton.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import SeedInput from "./SeedInput.jsx";
import GeneratorJobResult from "./GeneratorJobResult.jsx";
import MusicExamples from "./MusicExamples.jsx";
import DownloadProgress from "./DownloadProgress.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import React,{useEffect,useRef,useState} from "react";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import {managementCommand} from "./managementCommand.js";
import {readGenerationProposal,audioProposalInputs} from "./generationProposal.mjs";

export function HeartmulaPage({embedded=false,session=""}={}){return <AudioGeneratorPage music embedded={embedded} session={session}/>;}
export default function SoundEffectPage({embedded=false,session=""}={}){return <AudioGeneratorPage embedded={embedded} session={session}/>;}

function AudioGeneratorPage({music=false,embedded=false,session:embeddedSession=""}){
  const service=music?"music-heartmula":"sfx-dasheng-audiogen";
  const formPath="/management/assistant/"+(music?"heartmula-input":"sfx-input");
  const query=new URLSearchParams(location.search);
  const session=embeddedSession || query.get("session") || "";
  const [form,setForm]=useState(null),[review,setReview]=useState(null);
  const tagCount=form?.prompt?.split(",").filter(tag=>tag.trim()).length || 0;
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState(""),[model,setModel]=useState(null);
  const [job,setJob]=useState(embedded ? "" : query.get("job") || "");
  const [historyRevision,setHistoryRevision]=useState(0);
  const handoff=useGpuHandoff(session,service,setJob,setNotice);
  const submitting=useRef(false),confirmation=useRef(null);
  if(!confirmation.current)confirmation.current=createConfirmationGate();
  const reviewRef=useRef(null),promptRef=useRef(null),prepareRef=useRef(null);
  useEffect(()=>{if(review)reviewRef.current?.focus();},[review]);
  function closeReview(){
    const preparing=review?.payload.action==="prepare";
    confirmation.current.cancel();setReview(null);
    handoff.clearReview();
    requestAnimationFrame(()=> (preparing?prepareRef:promptRef).current?.focus());
  }
  async function readJob(id){
    const response=await fetch(formPath+"/"+encodeURIComponent(id),{cache:"no-store"});
    const result=await response.json();
    if(!response.ok)throw new Error(result.detail || "저장된 입력을 확인할 수 없습니다.");
    return result;
  }
  function cleaned(message){
    setJob("");setNotice(message);setHistoryRevision(value=>value+1);
  }
  useEffect(()=>{
    const controller=new AbortController();
    if(embedded || !new URLSearchParams(location.search).get("job")){
      managementCommand(service,"active",{}).then(result=>{
        if(!controller.signal.aborted && result.id)setJob(current=>current || result.id);
      }).catch(error=>{if(!controller.signal.aborted)setNotice("진행 작업 조회 실패 · "+error.message);});
    }
    fetch(formPath,{signal:controller.signal}).then(response=>{
      if(!response.ok)throw new Error("기본 입력을 불러올 수 없습니다.");
      return response.json();
    }).then(async defaults=>{
      const id=query.get('proposal_job');
      if(!id || embedded){if(!controller.signal.aborted)setForm(defaults);return;}
      try{
        const offset=query.get('proposal_offset');
        if(!/^\d+$/.test(offset || ''))throw new Error('대화 이력 정보를 확인할 수 없습니다.');
        const proposal=await readGenerationProposal(managementCommand,{session,job:id,snapshot:query.get('proposal_snapshot'),offset:Number(offset),kind:'audio'});
        const inputs=audioProposalInputs(defaults,proposal,service);
        if(!controller.signal.aborted){setForm(inputs);setNotice('대화 제안 입력을 불러왔습니다. 내용을 검토한 뒤 접수하세요.');}
      }catch(error){if(!controller.signal.aborted){setForm(defaults);setNotice('대화 제안을 불러오지 못했습니다 · '+error.message);}}
    }).catch(error=>{if(!controller.signal.aborted)setNotice(error.message);});
    return ()=>controller.abort();
  },[]);
  function edit(key,value){setForm(current=>({...current,[key]:value}));}
  async function preview(event){
    event.preventDefault();setBusy(true);setNotice("");
    try{
      if(music){
        if(!tagCount || !form.lyrics.trim())throw new Error("음악 태그와 가사를 입력하세요.");
        const status=await managementCommand(service,"model-status",{});
        if(!generationReady(status))throw new Error(status.message || "모델 준비가 필요합니다.");
      }
      const payload={...form,seed:Number(form.seed),...(music?{duration_seconds:Number(form.duration_seconds)}:{}),action:"generate"};
      const response=await fetch(formPath,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      const result=await response.json();
      if(!response.ok)throw new Error(result.detail || "입력을 확인하세요.");
      await handoff.preview(payload);
      setReview({payload,prompt:result.final_prompt,confirmation:confirmation.current.open()});
    }catch(error){setNotice(error.message);}
    finally{setBusy(false);}
  }
  async function reviewPreparation(){
    setNotice("");setBusy(true);
    try{
      if(music){
        const status=await managementCommand(service,"model-status",{});
        if(!status.artifacts_ready)throw new Error("모델 관리에서 파일 다운로드를 먼저 완료하세요.");
      }
      setReview({payload:{action:"prepare"},confirmation:confirmation.current.open()});
    }catch(error){setNotice(error.message);}
    finally{setBusy(false);}
  }
  async function submit(){
    if(!review || submitting.current || (review.payload.action==="generate" && !generationReady(model)))return;
    if(!confirmation.current.claim(review.confirmation))return;
    submitting.current=true;setBusy(true);
    try{
      if(handoff.review){await handoff.approve(review.payload);setNotice("확인한 GPU 양도 요청을 접수했습니다.");return;}
      const result=await managementCommand(service,review.payload.action,review.payload);
      if(!result.id)throw new Error("작업 ID를 확인할 수 없습니다.");
      setJob(result.id);setNotice(review.payload.action==="prepare"?"모델 준비를 대기열에 등록했습니다.":"공용 GPU 대기열에 등록했습니다.");
    }catch(error){setNotice(error.message+" · 생성 이력에서 접수 여부를 확인하세요.");}
    finally{handoff.clearReview();submitting.current=false;setBusy(false);setReview(null);}
  }
  return <article className={"audio-generator-page"+(embedded ? "" : " audio-standalone")}><a href={"/management/assistant/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화</a>
    <h1 className={embedded ? "embedded-page-title" : undefined}>{music?"HeartMuLa 음악 생성":"Dasheng 효과음 생성"}</h1>
    {music ? <p>태그는 쉼표로 구분합니다. 원곡을 생성한 뒤 Demucs가 MR과 보컬을 분리합니다.</p> : <p>16kHz WAV · 길이 자동 예측 · <a href="https://huggingface.co/mispeech/Dasheng-AudioGen">Dasheng-AudioGen 모델과 Apache-2.0 라이선스</a></p>}
    <details><summary>모델 다운로드·준비</summary>
      <DownloadProgress service={service}/>
      <button ref={prepareRef} disabled={busy || Boolean(review) || Boolean(handoff.id)} onClick={reviewPreparation}>모델 준비 요청 검토</button>
    </details><ModelReadiness service={service} onStatus={setModel}/><GeneratorChangelog generator={service}/>
    {handoff.id && <GpuHandoffStatus session={session} id={handoff.id} service={service} status={handoff.status} onUpdate={handoff.update} onClose={handoff.close}/>}
    <fieldset disabled={busy || Boolean(review) || !form}>
      {music && <MusicExamples apply={request=>setForm(current=>({...current,...request}))}/> }
      <GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id) cleaned(message); else setNotice(message);}} key={historyRevision} service={service} readJob={readJob} externalResultId={job} restore={input=>{
        setForm(input);setNotice("저장된 생성 입력을 불러왔습니다.");
      }} inspectResult={record=>setJob(record.id)}/>
    </fieldset>
    {form && <form onSubmit={preview}><fieldset disabled={busy || Boolean(review) || Boolean(handoff.id)}>
      <label>{music?"음악 태그":"효과음 설명"} <textarea ref={promptRef} required maxLength={4000} value={form.prompt} onChange={e=>edit("prompt",e.target.value)}/>{music ? <small>태그 {tagCount}개</small> : <PromptWordCount text={form.prompt}/>}</label>
      <SeedInput value={form.seed} max={4294967295} onChange={value=>edit("seed",value)}/>
      {music ? <>
        <label>가사·구간 태그 <textarea required maxLength={20000} value={form.lyrics} onChange={e=>edit("lyrics",e.target.value)}/><PromptWordCount text={form.lyrics}/></label>
        <label>최대 출력 시간(초) <input type="number" min="5" max="300" step="any" required value={form.duration_seconds} onChange={e=>edit("duration_seconds",e.target.value)}/></label>
      </> : <label className="sound-loop"><input type="checkbox" checked={form.loop_request} onChange={e=>edit("loop_request",e.target.checked)}/>반복 구조 요청</label>}
      <label>이력 태그 <input value={form.tag} onChange={e=>edit("tag",e.target.value)}/></label>
      <ActionButton type="submit" reasons={audioInputIssues(form,music,model)}>생성 요청 검토</ActionButton>
    </fieldset></form>}
    {review && <section ref={reviewRef} tabIndex={-1} aria-label="생성 요청 확인"><h2>{review.payload.action==="prepare"?"모델 다운로드·준비":"생성 요청 확인"}</h2>
      {review.payload.action==="generate" && <>
        <p>시드 {review.payload.seed} · {music ? `최대 출력 시간 ${review.payload.duration_seconds}초` : `반복 구조 ${review.payload.loop_request ? "요청" : "없음"}`}{review.payload.tag?.trim() && ` · 이력 태그 ${review.payload.tag.trim()}`}</p>
        <h3>최종 모델 입력</h3><p>{review.prompt} · <PromptWordCount text={review.prompt} label="최종 프롬프트"/></p>
        {music && review.payload.lyrics && <><h3>가사·구간 태그</h3><pre>{review.payload.lyrics}</pre></>}
      </>}
      <GpuQueueSummary/>
      {handoff.review && <p>동의하면 진행 중인 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 {music?"음악":"효과음"}을 생성합니다. 작업이 끝나면 Qwen 3.8을 다시 GPU에 적재합니다.</p>}
      <GenerationReviewActions busy={busy} onCancel={closeReview} onConfirm={submit} confirmLabel={handoff.review ? "해제·생성·재적재에 동의" : undefined} disabledReason={review.payload.action==="generate" && !generationReady(model) ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : ""}/></section>}
    {notice && <p role="status">{notice}</p>}
    <GeneratorJobResult selectionControls job={job} service={service} kind="audio" onDeleted={cleaned}/>
  </article>;
}
