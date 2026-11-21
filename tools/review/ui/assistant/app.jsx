import VacePage from "./VacePage.jsx";
import AnimatePage from "./AnimatePage.jsx";
import WriterPage from "./WriterPage.jsx";
import FluxImagePage from "./FluxImagePage.jsx";
import SoundEffectPage, {HeartmulaPage} from "./SoundEffectPage.jsx";
import DwposePage from "./DwposePage.jsx";
import AnimateMockPage from "./AnimateMockPage.jsx";
import MockProgress from "./MockProgress.jsx";
import SourceHistory from "./SourceHistory.jsx";
import ExpressionCatalog from "./ExpressionCatalog.jsx";
import AnchorHistory from "./AnchorHistory.jsx";
import ServiceRegistry from "./ServiceRegistry.jsx";
import OperationsJobs from "./OperationsJobs.jsx";
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
        status:job.status?.status || "접수 확인 중",session:view.id,job:m.job_id,activity,table}}}];
  });
}
function jobLink(id,session){
  const params=new URLSearchParams({panel:"jobs",job:id});
  if(session)params.set("session",session);
  return "/management/frame/hermes-agent/?"+params;
}
function Message() {
  const message=useAuiState(s=>s.message);
  const meta=message.metadata?.custom || {};
  return <MessagePrimitive.Root className={"message "+message.role}>
    <b>{message.role==="user"?"나":"헤르메스"}</b><MessagePrimitive.Parts/>
    {meta.table && <ResultTable table={meta.table}/>}
    {!meta.table && meta.activity?.source_history_summary && <pre>{meta.activity.source_history_summary}</pre>}
    {meta.activity?.events?.length>0 && <details><summary>도구 사용 내역</summary>{meta.activity.events.map((e,i)=><p key={i}>{e.name} · {e.target || e.result}</p>)}</details>}
    {meta.status && <small>{meta.status} {meta.job && <> · <a href={jobLink(meta.job,meta.session)}>{meta.job}</a></>}</small>}
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
function initialToolCategory(){
  const category=query().get("category") || "all";
  return ({"music-generation":"sound-management","sound-effects":"sound-management","town-map-review":"map-review","field-map-review":"map-review",animation:"animation-tool"})[category] || category;
}
function App() {
  const [session,setSession]=useState(query().get("session") || "");
  const [sessions,setSessions]=useState([]), [view,setView]=useState({}), [tools,setTools]=useState([]);
  const [draft,setDraft]=useState(""),[search,setSearch]=useState(()=>query().get("search") || ""),[showTools,setShowTools]=useState(()=>query().has("category") || query().has("search") || query().get("panel")==="jobs");
  const [category,setCategory]=useState(initialToolCategory);
  const [archived,setArchived]=useState(false),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const [sessionQuery,setSessionQuery]=useState("");
  const [listRequest,setListRequest]=useState({offset:0,query:""}),[listPage,setListPage]=useState(null);
  const [listError,setListError]=useState("");
  function resetSessionList(){
    setSessionQuery("");setListRequest({offset:0,query:""});
  }
  const [queue,setQueue]=useState(null),[refresh,setRefresh]=useState(0);
  const [historyPage,setHistoryPage]=useState(null);
  const sending=useRef(false),text=useRef(null);
  const toolToggle=useRef(null),toolSearch=useRef(null);
  useEffect(()=>{if(showTools)toolSearch.current?.focus();},[showTools]);
  function handleToolKeys(event){
    if(event.key==="Escape" && !event.nativeEvent.isComposing){
      event.preventDefault();setShowTools(false);toolToggle.current?.focus();
    }
  }
  function select(next) {
    const url=new URL(location.href);
    if(next!==session && url.searchParams.get("panel")==="jobs")url.searchParams.delete("job");
    if(next)url.searchParams.set("session",next);else url.searchParams.delete("session");
    history.pushState(null,"",url);setSession(next);setView({});setHistoryPage(null);setQueue(null);setError("");
  }
  useEffect(()=>{const cb=()=>{setSearchMode(query().get("panel")==="jobs"?"jobs":"tools");setCategory(initialToolCategory());setSearch(query().get("search") || "");setShowTools(query().has("category") || query().has("search") || query().get("panel")==="jobs");setSession(query().get("session")||"");setView({});setHistoryPage(null);setQueue(null);};window.addEventListener("popstate",cb);return()=>window.removeEventListener("popstate",cb);},[]);
  useEffect(()=>{let active=true;fetch(base+"tools").then(r=>r.json()).then(v=>{if(active)setTools(v)}).catch(e=>{if(active)setError(e.message)});
    return()=>{active=false};},[]);
  useEffect(()=>{
    let active=true;
    setListPage(null);setSessions([]);setListError("");
    call(archived?"session-archived":"session-list",{...listRequest,limit:30}).then(page=>{
      if(!active)return;
      if(!Array.isArray(page.sessions) || (listRequest.snapshot && page.snapshot!==listRequest.snapshot))throw new Error("세션 목록이 변경되었습니다. 다시 검색하세요.");
      setSessions(page.sessions);setListPage(page);
    }).catch(problem=>{if(active)setListError(problem.message);});
    return ()=>{active=false;};
  },[archived,listRequest,refresh]);
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
      setListRequest(current=>({offset:0,query:current.query}));setRefresh(n => n + 1);
    } catch (e) {
      if ((query().get("session") || "") === session) setError(e.message);
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  async function lifecycle(record,action){
    if(busy)return;
    if(action==="delete"&&!window.confirm((record.title || record.id)+" 대화 기록을 영구 삭제할까요?"))return;
    setBusy(true);
    try{await call("session-"+action,{session_id:record.id,expected_update:record.updated_at});
      if(action==="restore"){setArchived(false);select(record.id)}else if(record.id===session)select("");
      setListRequest(current=>({offset:0,query:current.query}));setRefresh(n=>n+1);
    }catch(e){setError(e.message)}finally{setBusy(false);}
  }
  const [showForms,setShowForms]=useState(false);
  const [showGpu,setShowGpu]=useState(false);
  const [searchMode,setSearchMode]=useState(()=>query().get("panel")==="jobs"?"jobs":"tools");
  const appendSelection=(label,id)=>{edit([draft,label+" "+id].filter(Boolean).join("\n"));setShowTools(false);text.current.focus();};
  function chooseTool(label,identifier) {
    edit([draft,"사용할 도구: "+label+" ("+identifier+")\n"].filter(Boolean).join("\n"));
    setShowTools(false);
    text.current.focus();
  }
  function reviewLink(path){
    const url=new URL(path,location.origin);
    if(session)url.searchParams.set("session",session);
    return url.pathname+url.search;
  }
  function changeCategory(value){
    const url=new URL(location.href);
    url.searchParams.set("category",value);
    history.replaceState(null,"",url);setCategory(value);
  }
  const categories=new Map(tools.map(tool=>[tool.category,tool.category_label]));
  const terms=search.trim().toLowerCase().split(/\s+/);
  const matchedTools=tools.filter(tool=>(category==="all" || tool.category===category) &&
    terms.every(term=>[tool.label,tool.id,tool.description].join(" ").toLowerCase().includes(term)));
  const chosen=query().get("tool");
  return <main><aside><h2>대화 세션</h2><button disabled={busy} onClick={()=>{select("");setArchived(false);resetSessionList();}}>새 대화</button><button disabled={busy} onClick={()=>{resetSessionList();setArchived(!archived);}}>{archived?"대화 목록":"보관함"}</button>
    <form onSubmit={e=>{e.preventDefault();setListRequest({offset:0,query:sessionQuery.trim()});}}>
      <label>세션 검색 <input maxLength={100} placeholder="제목·메시지·세션 ID" value={sessionQuery} onChange={e=>setSessionQuery(e.target.value)}/></label>
      <button>검색</button>
    </form>
    {listError && <p role="alert">{listError}</p>}
    {listPage && Number.isInteger(listPage.total) && <p>검색 결과 {listPage.total}개{listPage.unreadable_count>0 && " · 읽을 수 없는 세션 "+listPage.unreadable_count+"개 제외"}</p>}
    {sessions.map(s=><div className="session" key={s.id}><button disabled={busy} aria-current={s.id===session?"page":undefined} onClick={()=>archived?lifecycle(s,"restore"):select(s.id)}>{archived?"복원 · ":""}{s.title || s.id}</button>
    <button disabled={busy} onClick={()=>lifecycle(s,archived?"delete":"archive")}>{archived?"삭제":"보관"}</button></div>)}
    {listPage && (listRequest.offset>0 || listPage.next_offset!=null) && <nav aria-label="세션 목록 페이지">
      <button disabled={!listRequest.offset} onClick={()=>setListRequest({...listRequest,offset:Math.max(0,listRequest.offset-30),snapshot:listPage.snapshot})}>이전</button>
      <button disabled={listPage.next_offset==null} onClick={()=>setListRequest({...listRequest,offset:listPage.next_offset,snapshot:listPage.snapshot})}>다음</button>
    </nav>}</aside>
    <article><header><h1>{view.title || "헤르메스와 대화"}</h1><button ref={toolToggle} aria-expanded={showTools} onClick={()=>{setShowGpu(false);setShowTools(!showTools)}}>도구 탐색</button>
    <button aria-expanded={showGpu} onClick={()=>{setShowTools(false);setShowGpu(!showGpu)}}>GPU 프로세스 정보</button>
    {session&&<button aria-expanded={showForms} onClick={()=>setShowForms(!showForms)}>입력 폼</button>}
    {session&&<button aria-expanded={Boolean(queue)} onClick={()=>setQueue(queue ? null : {run:""})}>대기열</button>}</header>
    {showGpu && <GpuPanel/>}
    {showTools && <section className="floating-panel" aria-label="도구 탐색" onKeyDown={handleToolKeys}>
      <input ref={toolSearch} aria-label="도구 검색" maxLength={100} placeholder="이름·기능 검색" value={search} onChange={e=>setSearch(e.target.value)}/>
      <button aria-expanded={searchMode==="capabilities"} onClick={()=>setSearchMode(searchMode==="capabilities"?"tools":"capabilities")}>관리 기능 검색</button>
      <button aria-expanded={searchMode==="anchors"} onClick={()=>setSearchMode(searchMode==="anchors"?"tools":"anchors")}>앵커 검수 이력</button>
      <button aria-expanded={searchMode==="expressions"} onClick={()=>setSearchMode(searchMode==="expressions"?"tools":"expressions")}>표정 프리셋</button>
      {searchMode==="expressions" && <ExpressionCatalog key={search} query={search} choose={appendSelection}/>}
      {searchMode==="anchors" && <AnchorHistory/>}
      <button aria-expanded={searchMode==="services"} onClick={()=>setSearchMode(searchMode==="services"?"tools":"services")}>서비스 등록 목록</button>
      <button aria-expanded={searchMode==="history"} onClick={()=>setSearchMode(searchMode==="history"?"tools":"history")}>생성 이력</button>
      <button aria-expanded={searchMode==="jobs"} onClick={()=>setSearchMode(searchMode==="jobs"?"tools":"jobs")}>운영 작업 이력</button>
      {searchMode==="jobs" && <OperationsJobs key={session+":"+(query().get("job") || "")} session={session} linkedJob={query().get("panel")==="jobs"?query().get("job"):null}/>}
      {searchMode==="history" && <SourceHistory session={session} choose={appendSelection}/>}
      {searchMode==="services" && <ServiceRegistry key={search} query={search}/>}
      {searchMode==="capabilities" && <CapabilitySearch search={search} choose={chooseTool}/>}
      {searchMode==="tools" && <label>도구 분류 <select value={category} onChange={e=>changeCategory(e.target.value)}>
        <option value="all">전체</option>
        {category!=="all" && !categories.has(category) && <option value={category}>{category}</option>}
        {Array.from(categories,([id,label])=><option key={id} value={id}>{label || id}</option>)}
      </select></label>}
      {searchMode==="tools" && <p role="status">검색 결과 {matchedTools.length}건</p>}
      {searchMode==="tools" && matchedTools.map(tool=>
        <div key={tool.id}>
          <button onClick={()=>chooseTool(tool.label,tool.id)}>{tool.label}</button>
          {tool.review_path && <a href={reviewLink(tool.review_path)}>화면 열기</a>}
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
  "/management/assistant/vace": VacePage,
  "/management/frame/wan22-animate2-generator": AnimatePage,
  "/management/frame/writer-agent": WriterPage,
  "/management/frame/flux-expression-generator": FluxImagePage,
  "/management/frame/flux-seamless-generator": FluxImagePage,
  "/management/frame/flux-character-generator": FluxImagePage,
  "/management/frame/flux-building-generator": FluxImagePage,
  "/management/frame/flux-mannequin-generator": FluxImagePage,
  "/management/frame/flux-billboard-generator": FluxImagePage,
  "/management/frame/flux-prop-generator": FluxImagePage,
  "/management/frame/flux-vegetation-generator": FluxImagePage,
  "/management/frame/flux-image-generator": FluxImagePage,
  "/management/assistant/flux-image": FluxImagePage,
  "/management/frame/music-heartmula": HeartmulaPage,
  "/management/assistant/heartmula": HeartmulaPage,
  "/management/frame/sfx-dasheng-audiogen": SoundEffectPage,
  "/management/assistant/sound-effect": SoundEffectPage,
  "/management/assistant/dwpose": DwposePage,
  "/management/frame/dwpose-generator": DwposePage,
  "/management/frame/mock-animate-validation": AnimateMockPage,
  "/management/frame/mock-dwpose-validation": ()=> <DwposePage mock/>,
  "/management/frame/mock-progress-validation": MockProgress,
  "/management/assistant/models": ModelPage,
  "/management/frame/model-management": ModelPage,
  "/management/frame/world-map": WorldMap,
  "/management/frame/prompt-translation": TranslationPage,
  "/management/assistant/translation": TranslationPage,
};
const Page = pages[location.pathname.replace(/\/$/, "")] || App;
createRoot(document.getElementById("root")).render(<Page/>);
