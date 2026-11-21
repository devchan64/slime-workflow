import SoundEffectPage from "./SoundEffectPage.jsx";
import DwposePage from "./DwposePage.jsx";
import MockProgress from "./MockProgress.jsx";
import SourceHistory from "./SourceHistory.jsx";
import ServiceRegistry from "./ServiceRegistry.jsx";
import CapabilitySearch from "./CapabilitySearch.jsx";
import ModelPage from "./ModelPage.jsx";
import TranslationPage from "./TranslationPage.jsx";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";
import WorldMap from "./WorldMap.jsx";
import GpuPanel from "./GpuPanel.jsx";
import QueuePanel from "./QueuePanel.jsx";
import FormLibrary from "./FormLibrary.jsx";
import React, {useEffect, useRef, useState} from "react";
import {createRoot} from "react-dom/client";
import {AssistantRuntimeProvider, ThreadPrimitive, MessagePrimitive, useAuiState, useExternalStoreRuntime} from "@assistant-ui/react";

const base = "/management/assistant/";
const id = () => crypto.randomUUID().replaceAll("-", "");
const query = () => new URLSearchParams(location.search);
function call(command, payload = {}) {
  return managementCommand("hermes-agent", "hermes-"+command, payload);
}
function messagesFrom(view) {
  const records = view.messages || [];
  const start = (view.message_count ?? records.length) - (view.offset || 0) - records.length;
  return records.flatMap((m,index) => {
    const job = m.job || {}, key=m.id || m.request_id || (view.id + "-" + (start + index));
    const activity = job.tool_activity || {};
    const page = activity.source_history_page;
    const table = activity.history_table || (page && {
      title:page.service+" 생성 이력", summary:"전체 "+page.total+"건 · 이번 조회 "+page.rows.length+"건",
      columns:["작업 ID","상태"], rows:page.rows.map(row=>[row.id,row.status])
    });
    const answer = job.final_response || "";
    const showAnswer = !table || (answer !== activity.source_history_summary && !activity.history_table_is_answer);
    return [{id:key+"-user",role:"user",content:m.text},
      {id:key+"-answer",role:"assistant",content:showAnswer ? answer : "",metadata:{custom:{
        status:job.status?.status || "접수 확인 중",job:m.job_id,activity,table}}}];
  });
}
function Message() {
  const message=useAuiState(s=>s.message);
  const meta=message.metadata?.custom || {};
  return <MessagePrimitive.Root className={"message "+message.role}>
    <b>{message.role==="user"?"나":"헤르메스"}</b><MessagePrimitive.Parts/>
    {meta.table && <ResultTable table={meta.table}/>}
    {!meta.table && meta.activity?.source_history_summary && <pre>{meta.activity.source_history_summary}</pre>}
    {meta.activity?.events?.length>0 && <details><summary>도구 사용 내역</summary>{meta.activity.events.map((e,i)=><p key={i}>{e.name} · {e.target || e.result}</p>)}</details>}
    {meta.status && <small>{meta.status} {meta.job && " · "+meta.job}</small>}
  </MessagePrimitive.Root>;
}
function Conversation({view}) {
  const messages=React.useMemo(()=>messagesFrom(view),[view]);
  const runtime=useExternalStoreRuntime({messages,isRunning:false,convertMessage:m=>m});
  return <AssistantRuntimeProvider runtime={runtime}><ThreadPrimitive.Root className="thread"><ThreadPrimitive.Viewport className="viewport">
    <ThreadPrimitive.Empty><h2>무엇을 도와드릴까요?</h2></ThreadPrimitive.Empty>
    <ThreadPrimitive.Messages components={{Message}}/>
  </ThreadPrimitive.Viewport></ThreadPrimitive.Root></AssistantRuntimeProvider>;
}
function App() {
  const [session,setSession]=useState(query().get("session") || "");
  const [sessions,setSessions]=useState([]), [view,setView]=useState({}), [tools,setTools]=useState([]);
  const [draft,setDraft]=useState(""),[search,setSearch]=useState(""),[showTools,setShowTools]=useState(false);
  const [archived,setArchived]=useState(false),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const [queue,setQueue]=useState(null),[refresh,setRefresh]=useState(0);
  const [historyPage,setHistoryPage]=useState(null);
  const sending=useRef(false),text=useRef(null);
  function select(next) {
    const url=new URL(location.href);
    if(next)url.searchParams.set("session",next);else url.searchParams.delete("session");
    history.pushState(null,"",url);setSession(next);setView({});setHistoryPage(null);setQueue(null);setError("");
  }
  useEffect(()=>{const cb=()=>{setSession(query().get("session")||"");setView({});setHistoryPage(null);setQueue(null);};window.addEventListener("popstate",cb);return()=>window.removeEventListener("popstate",cb);},[]);
  useEffect(()=>{let active=true;fetch(base+"tools").then(r=>r.json()).then(v=>{if(active)setTools(v)}).catch(e=>{if(active)setError(e.message)});
    return()=>{active=false};},[]);
  useEffect(()=>{let active=true;call(archived?"session-archived":"session-list").then(v=>{if(active)setSessions(v.sessions)}).catch(e=>{if(active)setError(e.message)});return()=>{active=false};},[archived,refresh]);
  useEffect(()=>{setDraft(sessionStorage.getItem("hermes-draft-"+session) || "");},[session]);
  useEffect(()=>{
    let active=true,timer;
    async function load() {
      try {
        const payload={session_id:session,...(historyPage || {})};
        const next=await call("session-view",payload);
        if(active && next.id===session) setView(next);
      } catch(problem) {
        if(active)setError(problem.message);
      } finally {
        if(active && !historyPage)timer=setTimeout(load,3000);
      }
    }
    if(session)load();
    return ()=>{active=false;clearTimeout(timer);};
  },[session,historyPage]);
  function changeHistory(page) {
    setError("");
    setView({});
    setHistoryPage(page);
  }
  function edit(v){setDraft(v);sessionStorage.setItem("hermes-draft-"+session,v)}
  async function send(){
    if(!draft.trim()||sending.current)return;
    if(!window.confirm("이 요청을 헤르메스 작업 대기열에 등록할까요?"))return;
    const pendingKey = "hermes-pending-" + session;
    const saved = sessionStorage.getItem(pendingKey);
    const item = saved ? JSON.parse(saved) : {session_id:session || id(), request_id:id(), prompt:draft};
    if (item.prompt !== draft) {
      setError("접수 결과를 확인하려면 이전 입력으로 다시 보내세요.");
      return;
    }
    sessionStorage.setItem(pendingKey, JSON.stringify(item));
    sending.current = true;
    setBusy(true);
    setError("");
    try {
      if (!session) await call("session-create", {session_id:item.session_id});
      await call("session-submit", item);
      sessionStorage.removeItem(pendingKey);
      sessionStorage.removeItem("hermes-draft-" + session);
      if ((query().get("session") || "") === session) {
        setDraft("");
        setHistoryPage(null);
        if (session !== item.session_id) select(item.session_id);
        setArchived(false);
      }
      setRefresh(n => n + 1);
    } catch (e) {
      if ((query().get("session") || "") === session) setError(e.message);
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  async function lifecycle(record,action){
    if(action==="delete"&&!window.confirm(record.title+" 대화 기록을 영구 삭제할까요?"))return;
    try{await call("session-"+action,{session_id:record.id,expected_update:record.updated_at});
      if(action==="restore"){setArchived(false);select(record.id)}else if(record.id===session)select("");
      setRefresh(n=>n+1);
    }catch(e){setError(e.message)}
  }
  const [showForms,setShowForms]=useState(false);
  const [showGpu,setShowGpu]=useState(false);
  const [searchMode,setSearchMode]=useState("tools");
  function chooseTool(label,identifier) {
    edit([draft,"사용할 도구: "+label+" ("+identifier+")\n"].filter(Boolean).join("\n"));
    setShowTools(false);
    text.current.focus();
  }
  const chosen=query().get("tool");
  return <main><aside><h2>대화 세션</h2><button disabled={busy} onClick={()=>{select("");setArchived(false);}}>새 대화</button><button onClick={()=>setArchived(!archived)}>{archived?"대화 목록":"보관함"}</button>
    {sessions.map(s=><div className="session" key={s.id}><button disabled={busy} aria-current={s.id===session?"page":undefined} onClick={()=>archived?lifecycle(s,"restore"):select(s.id)}>{s.title || s.id}</button>
    <button disabled={busy} onClick={()=>lifecycle(s,archived?"delete":"archive")}>{archived?"삭제":"보관"}</button></div>)}</aside>
    <article><header><h1>{view.title || "헤르메스와 대화"}</h1><button aria-expanded={showTools} onClick={()=>{setShowGpu(false);setShowTools(!showTools)}}>도구 탐색</button>
    <button aria-expanded={showGpu} onClick={()=>{setShowTools(false);setShowGpu(!showGpu)}}>GPU 프로세스 정보</button>
    {session&&<button aria-expanded={showForms} onClick={()=>setShowForms(!showForms)}>입력 폼</button>}
    {session&&<button aria-expanded={Boolean(queue)} onClick={()=>setQueue(queue ? null : {run:""})}>대기열</button>}</header>
    {showGpu && <GpuPanel/>}
    {showTools && <section className="floating-panel" aria-label="도구 탐색">
      <input aria-label="도구 검색" maxLength={100} placeholder="이름·기능 검색" value={search} onChange={e=>setSearch(e.target.value)}/>
      <button aria-expanded={searchMode==="capabilities"} onClick={()=>setSearchMode(searchMode==="capabilities"?"tools":"capabilities")}>관리 기능 검색</button>
      <button aria-expanded={searchMode==="services"} onClick={()=>setSearchMode(searchMode==="services"?"tools":"services")}>서비스 등록 목록</button>
      <button aria-expanded={searchMode==="history"} onClick={()=>setSearchMode(searchMode==="history"?"tools":"history")}>생성 이력</button>
      {searchMode==="history" && <SourceHistory session={session} choose={(label,id)=>{edit([draft,label+" "+id].filter(Boolean).join("\n"));setShowTools(false);text.current.focus();}}/>}
      {searchMode==="services" && <ServiceRegistry key={search} query={search}/>}
      {searchMode==="capabilities" && <CapabilitySearch search={search} choose={chooseTool}/>}
      {searchMode==="tools" && tools.filter(tool=>(tool.label+tool.id+tool.description).toLowerCase().includes(search.toLowerCase())).map(tool=>
        <div key={tool.id}>
          <button onClick={()=>chooseTool(tool.label,tool.id)}>{tool.label}</button>
          {tool.review_path && <a href={tool.review_path+(session?"?"+new URLSearchParams({session}):"")}>화면 열기</a>}
        </div>)}
    </section>}
    {session && <div hidden={!showForms}>{<FormLibrary key={session} session={session} messages={view.messages || []} call={call} openRun={run=>{setShowForms(false);setQueue({run});}} addToMessage={value=>edit([draft,value].filter(Boolean).join("\n"))}/>}</div>}
    {queue && session && <QueuePanel key={session+queue.run} session={session} initialRun={queue.run} call={call}/>}
    {(view.next_offset != null || historyPage) && <nav aria-label="대화 이력 페이지">
      {view.next_offset != null && <button onClick={()=>changeHistory({offset:view.next_offset,snapshot:view.snapshot})}>이전 메시지 보기</button>}
      {historyPage && <button onClick={()=>changeHistory(null)}>최신 대화로 돌아가기</button>}
    </nav>}
    <Conversation key={session} view={view}/>{error&&<p role="alert">{error}</p>}
    <form onSubmit={e=>{e.preventDefault();send()}}>{chosen&&<button type="button" onClick={()=>edit(draft+"\n사용할 도구: "+chosen+"\n")}>{chosen} 요청에 추가</button>}
    <textarea ref={text} aria-label="메시지" placeholder="헤르메스에게 메시지 보내기" value={draft} disabled={busy} onChange={e=>edit(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&(e.metaKey||e.ctrlKey)){e.preventDefault();send()}}}/>
    <button disabled={busy||!draft.trim()}>{busy?"접수 중":"보내기"}</button></form></article></main>
}
const pages = {
  "/management/frame/sfx-dasheng-audiogen": SoundEffectPage,
  "/management/assistant/sound-effect": SoundEffectPage,
  "/management/assistant/dwpose": DwposePage,
  "/management/frame/dwpose-generator": DwposePage,
  "/management/frame/mock-progress-validation": MockProgress,
  "/management/assistant/models": ModelPage,
  "/management/frame/model-management": ModelPage,
  "/management/frame/world-map": WorldMap,
  "/management/frame/prompt-translation": TranslationPage,
  "/management/assistant/translation": TranslationPage,
};
const Page = pages[location.pathname.replace(/\/$/, "")] || App;
createRoot(document.getElementById("root")).render(<Page/>);
