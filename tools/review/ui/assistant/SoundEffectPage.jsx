import MusicExamples from "./MusicExamples.jsx";
import DownloadProgress from "./DownloadProgress.jsx";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import React,{useEffect,useRef,useState} from "react";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import {managementCommand} from "./managementCommand.js";

export function HeartmulaPage(){return <AudioGeneratorPage music/>;}
export default function SoundEffectPage(){return <AudioGeneratorPage/>;}

function AudioGeneratorPage({music=false}){
  const service=music?"music-heartmula":"sfx-dasheng-audiogen";
  const formPath="/management/assistant/"+(music?"heartmula-input":"sfx-input");
  const query=new URLSearchParams(location.search);
  const [form,setForm]=useState(null),[review,setReview]=useState(null);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const [job,setJob]=useState(query.get("job") || "");
  const [historyRevision,setHistoryRevision]=useState(0);
  const submitting=useRef(false);
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
    if(!new URLSearchParams(location.search).get("job")){
      managementCommand(service,"active",{}).then(result=>{
        if(!controller.signal.aborted && result.id)setJob(current=>current || result.id);
      }).catch(error=>{if(!controller.signal.aborted)setNotice("진행 작업 조회 실패 · "+error.message);});
    }
    fetch(formPath,{signal:controller.signal}).then(response=>{
      if(!response.ok)throw new Error("기본 입력을 불러올 수 없습니다.");
      return response.json();
    }).then(setForm).catch(error=>{if(!controller.signal.aborted)setNotice(error.message);});
    return ()=>controller.abort();
  },[]);
  function edit(key,value){setForm(current=>({...current,[key]:value}));}
  async function preview(event){
    event.preventDefault();setBusy(true);setNotice("");
    try{
      if(music){
        if(!form.prompt.trim() || !form.lyrics.trim())throw new Error("음악 태그와 가사를 입력하세요.");
        const status=await managementCommand(service,"model-status",{});
        if(!status.ready)throw new Error(status.message || "모델 준비가 필요합니다.");
      }
      const payload={...form,seed:Number(form.seed),...(music?{duration_seconds:Number(form.duration_seconds)}:{}),action:"generate"};
      const response=await fetch(formPath,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      const result=await response.json();
      if(!response.ok)throw new Error(result.detail || "입력을 확인하세요.");
      setReview({payload,prompt:result.final_prompt});
    }catch(error){setNotice(error.message);}
    finally{setBusy(false);}
  }
  async function submit(){
    if(!review || submitting.current)return;
    submitting.current=true;setBusy(true);
    try{
      const result=await managementCommand(service,review.payload.action,review.payload);
      if(!result.id)throw new Error("작업 ID를 확인할 수 없습니다.");
      setJob(result.id);setNotice(review.payload.action==="prepare"?"모델 준비를 대기열에 등록했습니다.":"공용 GPU 대기열에 등록했습니다.");
    }catch(error){setNotice(error.message+" · 생성 이력에서 접수 여부를 확인하세요.");}
    finally{submitting.current=false;setBusy(false);setReview(null);}
  }
  return <article><a href={"/management/assistant/"+(query.has("session")?"?"+new URLSearchParams({session:query.get("session")}):"")}>헤르메스 대화</a>
    <h1>{music?"HeartMuLa 음악 생성":"Dasheng 효과음 생성"}</h1>
    {music ? <p>태그는 쉼표로 구분합니다. 원곡을 생성한 뒤 Demucs가 MR과 보컬을 분리합니다.</p> : <p>16kHz WAV · 길이 자동 예측 · <a href="https://huggingface.co/mispeech/Dasheng-AudioGen">Dasheng-AudioGen 모델과 Apache-2.0 라이선스</a></p>}
    <details><summary>모델 다운로드·준비</summary>
      <DownloadProgress service={service}/>
      <button disabled={busy || Boolean(review)} onClick={()=>setReview({payload:{action:"prepare"}})}>모델 준비 요청 검토</button>
    </details><ModelReadiness service={service}/><GeneratorChangelog generator={service}/>
    <fieldset disabled={busy || Boolean(review) || !form}>
      {music && <MusicExamples apply={request=>setForm(current=>({...current,...request}))}/> }
      <GeneratorHistory key={historyRevision} service={service} readJob={readJob} restore={input=>{
        setForm(input);setNotice("저장된 생성 입력을 불러왔습니다.");
      }} inspectResult={record=>setJob(record.id)}/>
    </fieldset>
    {form && <form onSubmit={preview}><fieldset disabled={busy || Boolean(review)}>
      <label>{music?"음악 태그":"효과음 설명"} <textarea required maxLength={4000} value={form.prompt} onChange={e=>edit("prompt",e.target.value)}/></label>
      <label>시드 <input type="number" required min="0" max="4294967295" step="1" value={form.seed} onChange={e=>edit("seed",e.target.value)}/></label>
      {music ? <>
        <label>가사·구간 태그 <textarea required maxLength={20000} value={form.lyrics} onChange={e=>edit("lyrics",e.target.value)}/></label>
        <label>최대 출력 시간(초) <input type="number" min="5" max="300" step="any" required value={form.duration_seconds} onChange={e=>edit("duration_seconds",e.target.value)}/></label>
      </> : <label><input type="checkbox" checked={form.loop_request} onChange={e=>edit("loop_request",e.target.checked)}/>반복 구조 요청</label>}
      <label>이력 태그 <input value={form.tag} onChange={e=>edit("tag",e.target.value)}/></label>
      <button>생성 요청 검토</button>
    </fieldset></form>}
    {review && <section><h2>{review.payload.action==="prepare"?"모델 다운로드·준비":"최종 모델 입력"}</h2>{review.prompt && <p>{review.prompt}</p>}{music && review.payload.lyrics && <pre>{review.payload.lyrics}</pre>}<GpuQueueSummary/>
      <button disabled={busy} onClick={()=>setReview(null)}>입력 수정</button>
      <button disabled={busy} onClick={submit}>확인 후 대기열에 추가</button></section>}
    {notice && <p role="status">{notice}</p>}
    {job ? <MediaJobResult key={job} kind="audio" service={service} id={job}>
      {(record,refresh)=><React.Fragment key={record?.status || ""}>
        {record && <GeneratorJobControls service={service} id={job} state={record.status} refresh={refresh}/>}
        <HistoryCleanup service={service} job={job} state={record?.status} onDeleted={cleaned}/>
      </React.Fragment>}
    </MediaJobResult> : <HistoryCleanup service={service} onDeleted={cleaned}/>}
  </article>;
}
