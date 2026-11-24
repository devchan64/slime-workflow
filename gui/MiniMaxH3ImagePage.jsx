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
  const [pending,setPending]=useState(null), [preview,setPreview]=useState(""), [busy,setBusy]=useState(false), [error,setError]=useState("");
  const [job,setJob]=useState(""), [revision,setRevision]=useState(0);
  const sending=useRef(false);
  async function review(event){
    event.preventDefault();
    if(sending.current || busy || pending || !model?.generation_ready || !prompt.trim() || !Number.isInteger(seed) || seed<0 || seed>4294967295)return;
    sending.current=true;setBusy(true);setError("");
    const request={action:"generate",prompt:prompt.trim(),images:[],width:1024,height:1024,steps:6,seed};
    try{
      const result=await managementCommand(service,"preview",request);
      if(typeof result?.prompt!=="string" || !result.prompt || !/^[a-f0-9]{64}$/.test(result?.prompt_sha256 || ""))throw new Error("최종 프롬프트를 확인할 수 없습니다.");
      setPreview(result.prompt);setPending({...request,expected_prompt_sha256:result.prompt_sha256});
    }catch(problem){setError(problem.message || "공용 화풍을 적용한 프롬프트를 확인할 수 없습니다.");}
    finally{sending.current=false;setBusy(false);}
  }
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
    <form onSubmit={review}><fieldset disabled={busy || !!pending}>
      <label>프롬프트<textarea required maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <PromptWordCount text={prompt}/>
      <SeedInput value={seed} max={4294967295} onChange={value=>setSeed(value===""?"":Number(value))}/>
      <p>1024×1024 · 6스텝 · INT8 · 실제 ROCm 생성 미검증</p>
      {!model?.generation_ready && <p>모델 파일 준비 상태를 확인하세요.</p>}
      <button type="submit" disabled={!model?.generation_ready || busy || !!pending || !prompt.trim() || !Number.isInteger(seed) || seed<0 || seed>4294967295}>생성 요청 검토</button>
    </fieldset></form>
    {pending && <section aria-label="생성 요청 확인"><h2>공용 화풍 적용 프롬프트</h2><GpuQueueSummary/><pre className="generation-review-text">{preview}</pre><PromptWordCount text={preview} label="최종 프롬프트"/><p>1024×1024 · 6스텝 · 시드 {pending.seed}</p><GenerationReviewActions busy={busy} onCancel={()=>{setPending(null);setPreview("");}} onConfirm={submit}/></section>}
    <GeneratorHistory key={revision} service={service} statusCommand="status" card allowPriority openResult={setJob} resultId={job} onCloseResult={()=>setJob("")}
      onSelectedDeleted={(id)=>{if(id===job)setJob("");setRevision(n=>n+1);}}
      footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={()=>{setJob("");setRevision(n=>n+1);}}/>}
      renderResult={(id,close)=><section><button type="button" onClick={close}>결과 닫기</button><MediaJobResult kind="image" service={service} id={id}/></section>}/>
  </article>;
}
