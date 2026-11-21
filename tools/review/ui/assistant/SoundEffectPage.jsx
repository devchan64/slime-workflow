import React,{useEffect,useRef,useState} from "react";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import {managementCommand} from "./managementCommand.js";

const service="sfx-dasheng-audiogen";
const formPath="/management/assistant/sfx-input";

export default function SoundEffectPage(){
  const query=new URLSearchParams(location.search);
  const [form,setForm]=useState(null),[review,setReview]=useState(null);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const [job,setJob]=useState(query.get("job") || "");
  const submitting=useRef(false);
  useEffect(()=>{
    const controller=new AbortController();
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
      const payload={...form,seed:Number(form.seed),action:"generate"};
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
      const result=await managementCommand(service,"generate",review.payload);
      if(!result.id)throw new Error("작업 ID를 확인할 수 없습니다.");
      setJob(result.id);setNotice("효과음을 공용 GPU 대기열에 등록했습니다.");
    }catch(error){setNotice(error.message+" · 생성 이력에서 접수 여부를 확인하세요.");}
    finally{submitting.current=false;setBusy(false);setReview(null);}
  }
  return <article><a href={"/management/assistant/"+(query.has("session")?"?"+new URLSearchParams({session:query.get("session")}):"")}>헤르메스 대화</a>
    <h1>Dasheng 효과음 생성</h1><ModelReadiness service={service}/><GeneratorChangelog generator={service}/>
    {form && <form onSubmit={preview}><fieldset disabled={busy || Boolean(review)}>
      <label>효과음 설명 <textarea required maxLength={4000} value={form.prompt} onChange={e=>edit("prompt",e.target.value)}/></label>
      <label>시드 <input type="number" required min="0" max="4294967295" step="1" value={form.seed} onChange={e=>edit("seed",e.target.value)}/></label>
      <label><input type="checkbox" checked={form.loop_request} onChange={e=>edit("loop_request",e.target.checked)}/>반복 구조 요청</label>
      <label>이력 태그 <input value={form.tag} onChange={e=>edit("tag",e.target.value)}/></label>
      <button>생성 요청 검토</button>
    </fieldset></form>}
    {review && <section><h2>최종 모델 입력</h2><p>{review.prompt}</p><GpuQueueSummary/>
      <button disabled={busy} onClick={()=>setReview(null)}>입력 수정</button>
      <button disabled={busy} onClick={submit}>확인 후 대기열에 추가</button></section>}
    {notice && <p role="status">{notice}</p>}
    {job && <MediaJobResult key={job} kind="audio" service={service} id={job}/>}
  </article>;
}
