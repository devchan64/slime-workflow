import {JobPriority} from "./QueuePriority.jsx";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import React, {useEffect,useRef,useState} from "react";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import TranslationEvidence from "./TranslationEvidence.jsx";
import TranslationResult from "./TranslationResult.jsx";
import {managementCommand} from "./managementCommand.js";

const service="prompt-translation";
const callHermes=(command,payload)=>managementCommand("hermes-agent","hermes-"+command,payload);

export default function TranslationPage() {
  const query=new URLSearchParams(location.search);
  const [text,setText]=useState(""),[language,setLanguage]=useState("en"),[terms,setTerms]=useState("");
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const [job,setJob]=useState(query.get("job") || ""),[record,setRecord]=useState(null);
  const [revision,setRevision]=useState(0),[gpu,setGpu]=useState("");
  const sending=useRef(false);
  useEffect(()=>{document.title="프롬프트 번역";},[]);
  useEffect(()=>{
    if(!job)return;
    let active=true,timer;
    async function read(){
      try{
        const next=await managementCommand(service,"translation-status",{id:job});
        if(!active)return;
        if(next.id!==job)throw new Error("작업 ID가 일치하지 않습니다.");
        setRecord(next);
        if(["queued","running"].includes(next.status.status))timer=setTimeout(read,5000);
      }catch(error){if(active)setNotice(error.message);}
    }
    read();return()=>{active=false;clearTimeout(timer);};
  },[job,revision]);
  useEffect(()=>{
    if(!pending)return;
    const controller=new AbortController();
    setGpu("GPU 대기열 조회 중…");
    fetch("/management/gpu-queue",{signal:controller.signal,cache:"no-store"}).then(async response=>{
      if(!response.ok)throw new Error();
      const data=await response.json();
      if(!Array.isArray(data.jobs)||!["idle","busy"].includes(data.gpu_status?.status))throw new Error();
      if(!controller.signal.aborted)setGpu((data.gpu_status.status==="busy"?"GPU 사용 중":"GPU 유휴")+" · 대기 작업 "+data.jobs.length+"건"+(data.truncated?" 이상":""));
    }).catch(()=>{if(!controller.signal.aborted)setGpu("GPU 상태 확인 불가");});
    return ()=>controller.abort();
  },[pending]);
  function review(){
    try{
      const glossary=terms.split(/\r?\n/).filter(line=>line.trim()).map(line=>{
        const pair=line.split("=>").map(term=>term.trim());
        if(pair.length!==2||pair.some(term=>!term))throw new Error("용어는 한 줄에 원문 => 번역어로 입력하세요.");
        return {source:pair[0],target:pair[1]};
      });
      setPending({text,target_language:language,glossary});setNotice("");
    }catch(error){setNotice(error.message);}
  }
  async function submit(){
    if(!pending||sending.current)return;
    sending.current=true;setBusy(true);
    try{
      const result=await managementCommand(service,"translation-submit",pending);
      setRecord(null);setJob(result.id);setNotice("번역 대기열에 등록했습니다.");
    }catch(error){setNotice(error.message+" · 이력을 조회해 접수 여부를 확인하세요.");}
    finally{setPending(null);sending.current=false;setBusy(false);}
  }
  function restore(input){
    setText(input.text);setLanguage(input.target_language);
    setTerms((input.glossary||[]).map(term=>term.source+" => "+term.target).join("\n"));
  }
  return <section style={{padding:"1rem",maxWidth:"60rem",margin:"auto"}}>
    <a href={"/management/assistant/"+(query.has("session")?"?"+new URLSearchParams({session:query.get("session")}):"")}>헤르메스 대화</a>
    <h1>프롬프트 번역</h1>
    <p>TranslateGemma 4B · ROCm BF16 · <a href="https://ai.google.dev/gemma/terms">Gemma 이용약관</a></p>
    <ModelReadiness service={service}/><GeneratorChangelog generator={service}/>
    <fieldset disabled={Boolean(pending)}><label>한국어 원문 <textarea value={text} onChange={e=>setText(e.target.value)}/></label>
      <label>목표 언어 <select value={language} onChange={e=>setLanguage(e.target.value)}><option value="en">영어</option><option value="zh-CN">중국어 간체</option></select></label>
      <label>확인할 용어 <textarea placeholder="원문 => 번역어" value={terms} onChange={e=>setTerms(e.target.value)}/></label>
      <p>원문 {text.trim().split(/\s+/).filter(Boolean).length}단어 · 최종 입력 {text.trim().split(/\s+/).filter(Boolean).length}단어</p>
      <TranslationEvidence key={text} source={text} call={callHermes}/>
      <GeneratorHistory service={service} statusCommand="translation-status" restore={restore} inspectResult={item=>{setJob(item.id);setRecord(item);}}/>
      <button disabled={!text.trim()} onClick={review}>번역 대기열에 추가</button>
    </fieldset>
    {pending && <section><p>{gpu}</p><p>{pending.text} · {pending.target_language}</p>
      <button disabled={busy} onClick={()=>setPending(null)}>추가하지 않기</button><button disabled={busy} onClick={submit}>확인 후 대기열에 추가</button>
    </section>}
    <p role="status">{notice}</p>
    {job && <section><h2>번역 작업</h2><code>{job}</code> <button onClick={()=>setRevision(v=>v+1)}>상태 갱신</button>
      {record && <p>{record.status.status} {record.status.error}</p>}
      {record?.id===job && record.status.status==="queued" &&
        <JobPriority key={job} service={service} id={job} call={callHermes}/>}
      {record?.id===job && <GeneratorJobControls key={job+"/"+record.status.status} service={service} id={job}
        state={record.status.status} refresh={()=>setRevision(value=>value+1)}/>}
      {record?.result && <TranslationResult key={job} job={job} text={record.result.text}/>}
    </section>}
  </section>;
}
