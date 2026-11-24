import React, {useRef, useState} from "react";
import GeneratorPageIdentity from "./GeneratorPageIdentity.jsx";
import GeneratorUsage from "./GeneratorUsage.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import ActiveGeneratorProgress from "./ActiveGeneratorProgress.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import SeedInput from "./SeedInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import {managementCommand} from "./managementCommand.js";

const service = "minimax-h3-image";
export default function MiniMaxH3ImagePage({embedded=false}={}) {
  const [prompt,setPrompt]=useState(""), [seed,setSeed]=useState(42), [model,setModel]=useState(null);
  const [pending,setPending]=useState(null), [busy,setBusy]=useState(false), [error,setError]=useState("");
  const [job,setJob]=useState(""), [revision,setRevision]=useState(0);
  const sending=useRef(false);
  async function submit(){
    if(!pending || sending.current)return;
    sending.current=true;setBusy(true);setError("");
    try{
      const result=await managementCommand(service,"generate",pending);
      if(typeof result?.id!=="string" || !result.id)throw new Error("접수 ID를 확인할 수 없습니다. 이력을 확인하세요.");
      setJob(result.id);setRevision(n=>n+1);setPending(null);
    }catch(problem){setError((problem.message || "접수 여부를 확인할 수 없습니다.")+" 재접수 전에 이력을 확인하세요.");}
    finally{sending.current=false;setBusy(false);}
  }
  return <article className="vace-page generator-page-common">
    <GeneratorPageIdentity service={service} embedded={embedded} changelogCard/>
    <GeneratorUsage generator={service}/>
    <ModelReadiness service={service} onStatus={setModel}/>
    <ActiveGeneratorProgress service={service} revision={revision} onOpenResult={setJob}/>
    {error && <p role="alert">{error}</p>}
    <form onSubmit={event=>{event.preventDefault();if(!busy && model?.generation_ready && prompt.trim() && Number.isInteger(seed) && seed>=0 && seed<=4294967295)setPending({action:"generate",prompt:prompt.trim(),images:[],width:1024,height:1024,steps:6,seed});}}>
      <label>프롬프트<textarea required maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <PromptWordCount text={prompt} final/>
      <SeedInput value={seed} max={4294967295} onChange={value=>setSeed(value===""?"":Number(value))}/>
      <p>1024×1024 · 6스텝 · INT8 · 실제 ROCm 생성 미검증</p>
      {!model?.generation_ready && <p>비상주 스트리밍 및 메모리 검증 후 생성할 수 있습니다.</p>}
      <button type="submit" disabled={!model?.generation_ready || busy || !!pending || !prompt.trim() || !Number.isInteger(seed) || seed<0 || seed>4294967295}>생성 요청 검토</button>
    </form>
    {pending && <section aria-label="생성 요청 확인"><h2>생성 요청 확인</h2><GpuQueueSummary/><p>{pending.prompt}</p><p>1024×1024 · 6스텝 · 시드 {seed}</p><GenerationReviewActions busy={busy} onCancel={()=>setPending(null)} onConfirm={submit}/></section>}
    <GeneratorHistory key={revision} service={service} statusCommand="status" card allowPriority openResult={setJob} resultId={job} onCloseResult={()=>setJob("")}
      onSelectedDeleted={(id)=>{if(id===job)setJob("");setRevision(n=>n+1);}}
      footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={()=>{setJob("");setRevision(n=>n+1);}}/>}
      renderResult={(id,close)=><section><button type="button" onClick={close}>결과 닫기</button><MediaJobResult kind="image" service={service} id={id}/></section>}/>
  </article>;
}
