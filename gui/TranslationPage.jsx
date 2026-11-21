import JobStatus from "./JobStatus.jsx";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import RecordFolder from "./RecordFolder.jsx";
import GenerationProgress from "./GenerationProgress.jsx";
import {useLiveRefresh} from "./LiveRefresh.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import ActionButton from "./ActionButton.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
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

export default function TranslationPage({embedded=false}={}) {
  const query=new URLSearchParams(location.search);
  const [text,setText]=useState(""),[language,setLanguage]=useState("en"),[terms,setTerms]=useState("");
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState(""),[model,setModel]=useState(null);
  const [job,setJob]=useState(embedded ? "" : query.get("job") || ""),[record,setRecord]=useState(null);
  const [revision,setRevision]=useState(0);
  const [historyRevision,setHistoryRevision]=useState(0);
  const sending=useRef(false);
  const live=useLiveRefresh(()=>setRevision(value=>value+1),Boolean(job) && (!record || ["queued","running"].includes(record.status?.status)));
  useEffect(()=>{if(!embedded)document.title="프롬프트 번역";},[embedded]);
  useEffect(()=>{
    if(!job)return;
    let active=true;
    async function read(){
      try{
        const next=await managementCommand(service,"translation-status",{id:job});
        if(!active)return;
        if(next.id!==job)throw new Error("작업 ID가 일치하지 않습니다.");
        setRecord(next);

      }catch(error){if(active)setNotice(error.message);}
    }
    read();return()=>{active=false;};
  },[job,revision]);
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
    <ModelReadiness service={service} onStatus={setModel}/><GeneratorChangelog generator={service}/>
    <fieldset disabled={Boolean(pending)}><label>한국어 원문 <textarea value={text} onChange={e=>setText(e.target.value)}/></label>
      <label>목표 언어 <select value={language} onChange={e=>setLanguage(e.target.value)}><option value="en">영어</option><option value="zh-CN">중국어 간체</option></select></label>
      <label>확인할 용어 <textarea placeholder="원문 => 번역어" value={terms} onChange={e=>setTerms(e.target.value)}/></label>
      <p><PromptWordCount text={text} final/></p>
      <TranslationEvidence key={text} source={text} call={callHermes}/>
      <GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id){setJob("");setRecord(null);}setNotice(message);setHistoryRevision(v=>v+1);}} key={historyRevision} service={service} statusCommand="translation-status" restore={restore} inspectResult={item=>{setJob(item.id);setRecord(item);}}/>
      <ActionButton reasons={[!text.trim() && "번역할 한국어 원문을 입력하세요."]} onClick={review}>번역 요청 검토</ActionButton>
    </fieldset>
    <HistoryCleanup allowSelected={false} key={job+"/"+(record?.status?.status || "")} service={service} job={job} state={record?.status?.status}
      onDeleted={message=>{setJob("");setRecord(null);setNotice(message);setHistoryRevision(v=>v+1);}}/>
    {pending && <section><GpuQueueSummary/><p>{pending.text} · {pending.target_language}</p>
      <GenerationReviewActions busy={busy} onCancel={()=>setPending(null)} onConfirm={submit} disabledReason={!model?.ready ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : ""}/>
    </section>}
    <p role="status">{notice}</p>
    {job && <section ref={!record ? live.ref : undefined}><h2>번역 작업</h2><JobIdentifier id={job}/><RecordFolder key={job} service={service} id={job}/><button onClick={()=>setRevision(v=>v+1)}>상태 갱신</button>
      {record && <><p><JobStatus state={record.status.status}/> {record.status.error}</p><GenerationProgress job={{status:record.status.status}} live={live} supportsProgress={false}/></>}
      {record?.id===job && <GeneratorJobControls showActions={false} key={job+"/"+record.status.status} service={service} id={job}
        state={record.status.status} refresh={()=>setRevision(value=>value+1)}/>}
      {record?.result && <TranslationResult key={job} job={job} text={record.result.text}/>}
    </section>}
  </section>;
}
