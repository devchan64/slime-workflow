import React,{useEffect,useState} from "react";
import KimodoPromptExamples from "./KimodoPromptExamples.jsx";
import {managementCommand} from "./managementCommand.js";

export default function KimodoGeneration({session}){
  const key="kimodo-generation-receipt-"+session;
  const [inputs,setInputs]=useState(null),[review,setReview]=useState(null),[busy,setBusy]=useState(false);
  const [receipt,setReceipt]=useState(()=>sessionStorage.getItem(key) || ""),[notice,setNotice]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    fetch("/management/assistant/kimodo-defaults",{signal:controller.signal}).then(async response=>{
      if(!response.ok)throw new Error("생성 기본값을 조회할 수 없습니다.");
      const defaults=await response.json();
      if(!controller.signal.aborted)setInputs(defaults);
    }).catch(error=>{if(!controller.signal.aborted)setNotice(error.message);});
    return ()=>controller.abort();
  },[]);
  function edit(field,value){
    setInputs(previous=>({...previous,[field]:value}));setReview(null);
  }
  async function perform(action){
    setBusy(true);setNotice("");
    try{await action();}catch(error){setNotice(error.message);}finally{setBusy(false);}
  }
  async function inspect(){
    setReview(null);
    const response=await fetch("/management/assistant/kimodo-proposal-review",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({...inputs,frames:Number(inputs.frames),steps:Number(inputs.steps),seed:Number(inputs.seed)})});
    const result=await response.json();
    if(!response.ok)throw new Error(result.detail || "생성 입력을 확인하세요.");
    const model=await fetch("/management/assistant/model-readiness/kimodo",{cache:"no-store"});
    if(!model.ok)throw new Error("모델 상태를 확인할 수 없습니다.");
    const status=await model.json();
    if(!(status.generation_ready ?? status.ready))throw new Error(status.message || "모델 준비가 필요합니다.");
    setReview(result.request);
  }
  async function submit(){
    const id=crypto.randomUUID().replaceAll("-","");
    sessionStorage.setItem(key,id);setReceipt(id);setReview(null);
    const result=await managementCommand("hermes-agent","hermes-delegate-kimodo",{request_id:id,request:review});
    setNotice(result.state==="accepted"?"GPU 대기열에 등록했습니다. 작업 "+result.job_id:"접수 상태를 조회하세요.");
  }
  return <section aria-label="Kimodo 모션 생성"><h2>모션 생성</h2>
    {inputs && <form onSubmit={e=>{e.preventDefault();perform(inspect);}}><fieldset disabled={busy}>
      <label>동작 설명 <textarea required maxLength={2000} value={inputs.prompt} onChange={e=>edit("prompt",e.target.value)}/></label>
      <KimodoPromptExamples apply={prompt=>edit("prompt",prompt)}/>
      {[["frames","프레임 수",30,300],["steps","생성 단계",2,100],["seed","시드",0,2147483647]].map(([field,label,min,max])=>
        <label key={field}>{label} <input type="number" required min={min} max={max} value={inputs[field]} onChange={e=>edit(field,e.target.value)}/></label>)}
      <button>생성 요청 검토</button>
    </fieldset></form>}
    {review && <section><pre>{JSON.stringify(review,null,2)}</pre>
      <button disabled={busy} onClick={()=>perform(submit)}>GPU 대기열에 등록</button>
      <button disabled={busy} onClick={()=>setReview(null)}>취소</button></section>}
    {receipt && <p>최근 접수 ID <code>{receipt}</code> <button disabled={busy} onClick={()=>perform(async()=>{
      const result=await managementCommand("hermes-agent","hermes-delegation-status",{request_id:receipt});
      setNotice([result.state,result.job_id].filter(Boolean).join(" · "));
    })}>접수 상태 조회</button></p>}
    {notice && <p role="status">{notice}</p>}
  </section>;
}
