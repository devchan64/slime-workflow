import QwenArchive from "./QwenArchive.jsx";
import KimodoPage from "./KimodoPage.jsx";
import KimodoProposal from "./KimodoProposal.jsx";
import BillboardCatalog from "./BillboardCatalog.jsx";
import SpriteSheetEditor from "./SpriteSheetEditor.jsx";
import KeyframeCatalog from "./KeyframeCatalog.jsx";
import ContentDatabaseStatus from "./ContentDatabaseStatus.jsx";
import EffectEditor from "./EffectEditor.jsx";
import BuildingEditor from "./BuildingEditor.jsx";
import MapReview from "./MapReview.jsx";
import BattlefieldReview from "./BattlefieldReview.jsx";
import FunControlPage from "./FunControlPage.jsx";
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
        status:job.status?.status || "접수 확인 중",session:view.id,job:m.job_id,kimodoProposal:job.status?.status==="completed" && !job.final_response_truncated && answer.includes("HERMES_KIMODO_PROPOSAL"),activity,table}}}];
  });
}
function jobLink(id,session){
  const params=new URLSearchParams({panel:"jobs",job:id});
  if(session)params.set("session",session);
  return "/management/frame/hermes-agent/?"+params;
}
const HistoryRoutes=React.createContext({});
const ProposalActions=React.createContext(null);
function Message() {
  const actions=React.useContext(ProposalActions);
  const message=useAuiState(s=>s.message);
  const meta=message.metadata?.custom || {};
  const paths=React.useContext(HistoryRoutes);
  const path=paths[meta.activity?.source_history_page?.service];
  const table=meta.table && path ? {...meta.table,rows:meta.table.rows.map(([job,...cells])=>[
    <a href={path+"?"+new URLSearchParams({job,session:meta.session})}>{job}</a>,...cells])} : meta.table;
  return <MessagePrimitive.Root className={"message "+message.role}>
    <b>{message.role==="user"?"나":"헤르메스"}</b><MessagePrimitive.Parts/>
    {meta.kimodoProposal && meta.job && <KimodoProposal key={meta.job} job={meta.job} append={actions.append} openStep={actions.openStep}/>}
    {table && <ResultTable table={table}/>}
    {!meta.table && meta.activity?.source_history_summary && <pre>{meta.activity.source_history_summary}</pre>}
    {meta.activity?.events?.length>0 && <details><summary>도구 사용 내역</summary>{meta.activity.events.map((e,i)=><p key={i}>{e.name} · {e.target || e.result}</p>)}</details>}
    {meta.status && <small>{meta.status} {meta.job && <> · <a href={jobLink(meta.job,meta.session)}>{meta.job}</a></>}</small>}
  </MessagePrimitive.Root>;
}
function Conversation({view}) {
  const messages=React.useMemo(()=>messagesFrom(view),[view]);
  const [routes,setRoutes]=useState({});
  const hasHistory=messages.some(message=>message.metadata?.custom?.activity?.source_history_page);
  useEffect(()=>{
    if(!hasHistory)return;
    const controller=new AbortController();
    fetch(base+"history-services",{signal:controller.signal}).then(response=>{
      if(!response.ok)throw new Error();
      return response.json();
    }).then(services=>{
      if(!controller.signal.aborted)setRoutes(Object.fromEntries(services.filter(row=>row.result_path).map(row=>[row.service,row.result_path])));
    }).catch(()=>{}); // Keep saved rows readable when the catalog is unavailable.
    return ()=>controller.abort();
  },[hasHistory]);
  const runtime=useExternalStoreRuntime({messages,isRunning:false,convertMessage:m=>m});
  return <HistoryRoutes.Provider value={routes}><AssistantRuntimeProvider runtime={runtime}><ThreadPrimitive.Root className="thread"><ThreadPrimitive.Viewport className="viewport">
    <ThreadPrimitive.Empty><h2>무엇을 도와드릴까요?</h2></ThreadPrimitive.Empty>
    <ThreadPrimitive.Messages components={{Message}}/>
  </ThreadPrimitive.Viewport></ThreadPrimitive.Root></AssistantRuntimeProvider></HistoryRoutes.Provider>;
}
function initialToolCategory(){
  const category=query().get("category") || "all";
  return ({"music-generation":"sound-management","sound-effects":"sound-management","town-map-review":"map-review","field-map-review":"map-review",animation:"animation-tool"})[category] || category;
}
function readPendingSubmission(raw,session){
  if(raw===null)return null;
  try{
    const item=JSON.parse(raw);
    if(typeof item?.prompt==="string" && item.prompt.trim() &&
       typeof item.session_id==="string" && /^[a-f0-9]{32}$/.test(item.session_id) &&
       (!session || item.session_id===session) && typeof item.request_id==="string" && /^[a-f0-9]{32}$/.test(item.request_id))
      return {session_id:item.session_id,request_id:item.request_id,prompt:item.prompt};
  }catch{}
  return null;
}
function App() {
  const [session,setSession]=useState(query().get("session") || "");
  const [sessions,setSessions]=useState([]), [view,setView]=useState({}), [tools,setTools]=useState([]);
  const [draft,setDraft]=useState(""),[search,setSearch]=useState(()=>query().get("search") || ""),[showTools,setShowTools]=useState(()=>query().has("category") || query().has("search") || ["jobs","capabilities"].includes(query().get("panel")));
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
  useEffect(()=>{const cb=()=>{setSearchMode(["jobs","capabilities"].includes(query().get("panel"))?query().get("panel"):"tools");setCategory(initialToolCategory());setSearch(query().get("search") || "");setShowTools(query().has("category") || query().has("search") || ["jobs","capabilities"].includes(query().get("panel")));setSession(query().get("session")||"");setView({});setHistoryPage(null);setQueue(null);};window.addEventListener("popstate",cb);return()=>window.removeEventListener("popstate",cb);},[]);
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
  const pendingKey = "hermes-pending-" + session;
  const pendingText = sessionStorage.getItem(pendingKey);
  const pending = readPendingSubmission(pendingText,session);
  const invalidPending = pendingText!==null && !pending;
  async function send(retry=false){
    if(invalidPending || sending.current || (!retry && !draft.trim()))return;
    if(pending && pending.prompt!==draft && !retry)return;
    const item = pending || {session_id:session || id(), request_id:id(), prompt:draft};
    sessionStorage.setItem(pendingKey, JSON.stringify(item));
    sending.current = true;
    setBusy(true);
    setError("");
    try {
      if (!session) await call("session-create", {session_id:item.session_id});
      await call("session-submit", item);
      sessionStorage.removeItem(pendingKey);
      const currentDraft=sessionStorage.getItem("hermes-draft-"+session) || "";
      const remaining=currentDraft===item.prompt?"":currentDraft;
      if(!remaining || session!==item.session_id)sessionStorage.removeItem("hermes-draft-"+session);
      if(remaining && session!==item.session_id)sessionStorage.setItem("hermes-draft-"+item.session_id,remaining);
      if ((query().get("session") || "") === session) {
        setDraft(remaining);
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
    try{
      const receipt=await call("session-"+action,{session_id:record.id,expected_update:record.updated_at});
      if(receipt.session_id!==record.id || receipt.operation!==action)throw new Error("세션 처리 결과를 확인하세요.");
      if(action==="delete"){
        sessionStorage.removeItem("hermes-draft-"+record.id);
        sessionStorage.removeItem("hermes-pending-"+record.id);
      }
      if(action==="restore"){setArchived(false);select(record.id)}else if(record.id===session)select("");
      setListRequest(current=>({offset:0,query:current.query}));setRefresh(n=>n+1);
    }catch(e){setError(e.message)}finally{setBusy(false);}
  }
  const [proposalStep,setProposalStep]=useState(null);
  const [showForms,setShowForms]=useState(false);
  const [showGpu,setShowGpu]=useState(false);
  const [searchMode,setSearchMode]=useState(()=>["jobs","capabilities"].includes(query().get("panel"))?query().get("panel"):"tools");
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
  const [folded,setFolded]=useState(()=>localStorage.getItem("hermes-session-folded")==="true");
  const [sidebarWidth,setSidebarWidth]=useState(()=>{
    const saved=Number(localStorage.getItem("hermes-session-width"));
    return saved>=200 && saved<=600?saved:288;
  });
  function resizeSidebar(width){
    setSidebarWidth(Math.max(200,Math.min(600,Math.floor(window.innerWidth*0.48),Math.round(width))));
  }
  useEffect(()=>{localStorage.setItem("hermes-session-width",String(sidebarWidth));},[sidebarWidth]);
  return <main className={"hermes-chat"+(folded?" sessions-folded":"")} style={{"--sessions-width":sidebarWidth+"px"}}>
    <aside id="hermes-session-list" hidden={folded}><h2>대화 세션</h2><button disabled={busy} onClick={()=>{select("");setArchived(false);resetSessionList();}}>새 대화</button><button disabled={busy} onClick={()=>{resetSessionList();setArchived(!archived);}}>{archived?"대화 목록":"보관함"}</button>
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
    {!folded && <div className="session-divider" role="separator" tabIndex={0} aria-label="세션 목록 너비"
      aria-controls="hermes-session-list" aria-orientation="vertical" aria-valuemin={200} aria-valuemax={Math.min(600,Math.floor(window.innerWidth*0.48))}
      aria-valuenow={Math.min(sidebarWidth,Math.floor(window.innerWidth*0.48))}
      onPointerDown={event=>{if(event.button===0){event.preventDefault();event.currentTarget.focus();event.currentTarget.setPointerCapture(event.pointerId);}}}
      onPointerMove={event=>{if(event.currentTarget.hasPointerCapture(event.pointerId))resizeSidebar(event.clientX-event.currentTarget.parentElement.getBoundingClientRect().left);}}
      onKeyDown={event=>{
        const current=event.currentTarget.previousElementSibling.getBoundingClientRect().width;
        const widths={ArrowLeft:current-16,ArrowRight:current+16,Home:200,End:600};
        if(Object.hasOwn(widths,event.key)){event.preventDefault();resizeSidebar(widths[event.key]);}
      }}/>}
    <article><header><button aria-controls="hermes-session-list" aria-expanded={!folded} onClick={()=>{
      localStorage.setItem("hermes-session-folded",String(!folded));setFolded(!folded);
    }}>{folded?"세션 목록 펼치기":"세션 목록 접기"}</button><h1>{view.title || "헤르메스와 대화"}</h1><details className="chat-actions"><summary>세션 도구</summary><div onClick={e=>{e.currentTarget.parentElement.open=false;}}>
    <button aria-expanded={showGpu} onClick={()=>{setShowTools(false);setShowGpu(!showGpu)}}>GPU 프로세스 정보</button>
    {session&&<button aria-expanded={showForms} onClick={()=>setShowForms(!showForms)}>입력 폼</button>}
    {session&&<button aria-expanded={Boolean(queue)} onClick={()=>setQueue(queue ? null : {run:""})}>대기열</button>}</div></details></header>
    {showGpu && <GpuPanel/>}
    {showTools && <section className="floating-panel" aria-label="도구 탐색" onKeyDown={handleToolKeys}>
      <input ref={toolSearch} aria-label="도구 검색" maxLength={100} placeholder="이름·기능 검색" value={search} onChange={e=>setSearch(e.target.value)}/>
      <button aria-expanded={searchMode==="capabilities"} onClick={()=>setSearchMode(searchMode==="capabilities"?"tools":"capabilities")}>관리 기능 검색</button>
      <button aria-expanded={searchMode==="anchors"} onClick={()=>setSearchMode(searchMode==="anchors"?"tools":"anchors")}>앵커 검수 이력</button>
      <button aria-expanded={searchMode==="expressions"} onClick={()=>setSearchMode(searchMode==="expressions"?"tools":"expressions")}>표정 프리셋</button>
      {searchMode==="expressions" && <ExpressionCatalog key={search} query={search} choose={appendSelection}/>}
      {searchMode==="anchors" && <AnchorHistory/>}
      <button aria-expanded={searchMode==="billboards"} onClick={()=>setSearchMode(searchMode==="billboards"?"tools":"billboards")}>빌보드 에셋</button>
      {searchMode==="billboards" && <BillboardCatalog choose={appendSelection}/>}
      <button aria-expanded={searchMode==="keyframes"} onClick={()=>setSearchMode(searchMode==="keyframes"?"tools":"keyframes")}>Kimodo 키프레임</button>
      {searchMode==="keyframes" && <KeyframeCatalog query={search} choose={appendSelection}/>}
      <button aria-expanded={searchMode==="content"} onClick={()=>setSearchMode(searchMode==="content"?"tools":"content")}>콘텐츠 DB 상태</button>
      {searchMode==="content" && <ContentDatabaseStatus/>}
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
    {session && <div hidden={!showForms}>{<FormLibrary key={session} proposalStep={proposalStep?.session===session ? proposalStep : null} session={session} messages={view.messages || []} call={call} openRun={run=>{setShowForms(false);setQueue({run});}} addToMessage={value=>{edit([draft,value].filter(Boolean).join("\n"));setShowForms(false);text.current?.focus();}}/>}</div>}
    {queue && session && <QueuePanel key={session+queue.run} session={session} initialRun={queue.run} call={call}/>}
    {(view.next_offset != null || historyPage) && <nav aria-label="대화 이력 페이지">
      {view.next_offset != null && <button onClick={()=>changeHistory({offset:view.next_offset,snapshot:view.snapshot})}>이전 메시지 보기</button>}
      {historyPage && <button onClick={()=>changeHistory(null)}>최신 대화로 돌아가기</button>}
    </nav>}
    <ProposalActions.Provider value={{append:appendSelection,openStep:inputs=>{setProposalStep({session,inputs});setShowForms(true);}}}><Conversation key={session} view={view}/></ProposalActions.Provider>{error&&<p role="alert">{error}</p>}
    <form onSubmit={e=>{e.preventDefault();send()}}>{chosen&&<button type="button" onClick={()=>edit(draft+"\n사용할 도구: "+chosen+"\n")}>{chosen} 요청에 추가</button>}
    <button type="button" ref={toolToggle} aria-expanded={showTools} onClick={()=>{setShowGpu(false);setShowTools(!showTools)}}>도구 탐색</button>
    <textarea ref={text} aria-label="메시지" placeholder="헤르메스에게 메시지 보내기" value={draft} disabled={busy} onChange={e=>edit(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&(e.metaKey||e.ctrlKey)){e.preventDefault();send()}}}/>
    {invalidPending && <div role="alert">이 탭의 접수 기록을 읽을 수 없습니다. 대화 이력에서 이전 요청의 접수 여부를 확인하세요.
      <button type="button" onClick={()=>{sessionStorage.removeItem(pendingKey);setRefresh(n=>n+1);}}>탭의 손상된 접수 기록 지우기</button></div>}
    {pending && pending.prompt!==draft && <details><summary>접수 확인이 필요한 이전 요청</summary>
      <pre>{pending.prompt}</pre><button type="button" disabled={busy} onClick={()=>send(true)}>이전 요청 접수 다시 확인</button></details>}
    <button disabled={busy||invalidPending||!draft.trim()||Boolean(pending && pending.prompt!==draft)}>{busy?"접수 중":pending && pending.prompt===draft?"같은 요청 다시 보내기":"보내기"}</button></form></article></main>
}
const pages = {
  "/management/frame/kimodo-generator": KimodoPage,
  "/management/assistant/qwen-archive": QwenArchive,
  "/management/assistant/kimodo": KimodoPage,
  "/management/frame/effect-editor": EffectEditor,
  "/management/frame/sprite-sheet-editor": SpriteSheetEditor,
  "/management/assistant/sprite-sheets": SpriteSheetEditor,
  "/management/assistant/effects": EffectEditor,
  "/management/frame/building-editor": BuildingEditor,
  "/management/frame/asset-editor": BillboardCatalog,
  "/management/assistant/billboards": BillboardCatalog,
  "/management/assistant/buildings": BuildingEditor,
  "/management/assistant/field-map": MapReview,
  "/management/assistant/town-map": MapReview,
  "/management/assistant/battlefield": BattlefieldReview,
  "/management/frame/wan22-fun-control-generator": FunControlPage,
  "/management/assistant/fun-control": FunControlPage,
  "/management/frame/wan22-vace-generator": VacePage,
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
