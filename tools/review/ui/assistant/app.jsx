import React, {useEffect, useRef, useState} from "react";
import {createRoot} from "react-dom/client";
import {AssistantRuntimeProvider, ThreadPrimitive, MessagePrimitive, useAuiState, useExternalStoreRuntime} from "@assistant-ui/react";

const base = "/management/assistant/";
const id = () => crypto.randomUUID().replaceAll("-", "");
const query = () => new URLSearchParams(location.search);
async function call(command, payload = {}) {
  const res = await fetch("/management/command", {method:"POST", headers:{"Content-Type":"application/json"},body:JSON.stringify({service:"hermes-agent",command:"hermes-"+command,payload})});
  const value = await res.json();
  if (!res.ok) throw new Error(value.error || value.detail || "요청을 처리할 수 없습니다.");
  return value;
}
function messagesFrom(view) {
  return (view.messages || []).flatMap((m) => {
    const job = m.job || {}, key=m.id || m.request_id || m.job_id;
    return [{id:key+"-user",role:"user",content:m.text},
      {id:key+"-answer",role:"assistant",content:job.final_response || "",metadata:{custom:{
        status:job.status?.status || "접수 확인 중",job:m.job_id,activity:job.tool_activity || {}}}}];
  });
}
function Message() {
  const message=useAuiState(s=>s.message);
  const meta=message.metadata?.custom || {}, page=meta.activity?.source_history_page;
  return <MessagePrimitive.Root className={"message "+message.role}>
    <b>{message.role==="user"?"나":"헤르메스"}</b><MessagePrimitive.Parts/>
    {page && <section><strong>{page.service} 생성 이력</strong><p>전체 {page.total}건 · 이번 조회 {page.rows.length}건</p><table><thead><tr><th>작업 ID</th><th>상태</th></tr></thead><tbody>{page.rows.map((r,i)=><tr key={i}><td>{r.id}</td><td>{r.status}</td></tr>)}</tbody></table></section>}
    {!page && meta.activity?.source_history_summary && <pre>{meta.activity.source_history_summary}</pre>}
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
  const sending=useRef(false),text=useRef(null);
  function select(next) {
    const url=new URL(location.href);
    if(next)url.searchParams.set("session",next);else url.searchParams.delete("session");
    history.pushState(null,"",url);setSession(next);setView({});setQueue(null);setError("");
  }
  useEffect(()=>{const cb=()=>{setSession(query().get("session")||"");setView({});setQueue(null);};window.addEventListener("popstate",cb);return()=>window.removeEventListener("popstate",cb);},[]);
  useEffect(()=>{let active=true;fetch(base+"tools").then(r=>r.json()).then(v=>{if(active)setTools(v)}).catch(e=>{if(active)setError(e.message)});
    return()=>{active=false};},[]);
  useEffect(()=>{let active=true;call(archived?"session-archived":"session-list").then(v=>{if(active)setSessions(v.sessions)}).catch(e=>{if(active)setError(e.message)});return()=>{active=false};},[archived,refresh]);
  useEffect(()=>{let active=true,timer;setDraft(sessionStorage.getItem("hermes-draft-"+session) || "");
    async function poll(){try{const v=await call("session-view",{session_id:session});if(active && v.id===session)setView(v)}catch(e){if(active)setError(e.message)}finally{if(active)timer=setTimeout(poll,3000)}}
    if(session)poll();return()=>{active=false;clearTimeout(timer)};},[session]);
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
  const chosen=query().get("tool");
  return <main><aside><h2>대화 세션</h2><button disabled={busy} onClick={()=>{select("");setArchived(false);}}>새 대화</button><button onClick={()=>setArchived(!archived)}>{archived?"대화 목록":"보관함"}</button>
    {sessions.map(s=><div className="session" key={s.id}><button disabled={busy} aria-current={s.id===session?"page":undefined} onClick={()=>archived?lifecycle(s,"restore"):select(s.id)}>{s.title || s.id}</button>
    <button disabled={busy} onClick={()=>lifecycle(s,archived?"delete":"archive")}>{archived?"삭제":"보관"}</button></div>)}</aside>
    <article><header><h1>{view.title || "헤르메스와 대화"}</h1><button onClick={()=>setShowTools(!showTools)}>도구 탐색</button>
    {session&&<button onClick={async()=>{try{const result=await call("workflow-list",{session_id:session,category:"",state:""});if(query().get("session")===session)setQueue(result.steps)}catch(e){setError(e.message)}}}>대기열</button>}</header>
    {showTools&&<section className="panel"><input aria-label="도구 검색" placeholder="이름·기능 검색" value={search} onChange={e=>setSearch(e.target.value)}/>{tools.filter(t=>(t.label+t.id+t.description).toLowerCase().includes(search.toLowerCase())).map(t=><button key={t.id} onClick={()=>{edit((draft?draft+"\n":"")+"사용할 도구: "+t.label+" ("+t.id+")\n");setShowTools(false);text.current.focus()}}>{t.label}</button>)}</section>}
    {queue&&<section className="panel"><button onClick={()=>setQueue(null)}>대기열 닫기</button>{queue.length?queue.map(s=><p key={s.request_id}>{s.generator} · {s.step_id} · {s.state}</p>):<p>이 세션의 작업이 없습니다.</p>}</section>}
    <Conversation key={session} view={view}/>{error&&<p role="alert">{error}</p>}
    <form onSubmit={e=>{e.preventDefault();send()}}>{chosen&&<button type="button" onClick={()=>edit(draft+"\n사용할 도구: "+chosen+"\n")}>{chosen} 요청에 추가</button>}
    <textarea ref={text} aria-label="메시지" placeholder="헤르메스에게 메시지 보내기" value={draft} disabled={busy} onChange={e=>edit(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&(e.metaKey||e.ctrlKey)){e.preventDefault();send()}}}/>
    <button disabled={busy||!draft.trim()}>{busy?"접수 중":"보내기"}</button></form></article></main>
}
createRoot(document.getElementById("root")).render(<App/>);
