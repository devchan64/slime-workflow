import React,{useEffect,useId,useRef,useState} from "react";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";

import {readArchiveJob} from "./readArchiveJob.mjs";
import {qwenArchiveUrl} from "./qwenArchiveUrl.mjs";

function ArchiveDetail({service,id}){
  const [log,setLog]=useState(null),[error,setError]=useState(""),[loading,setLoading]=useState(false);
  const statusId=useId(),errorId=useId();
  const request=useRef(null);
  useEffect(()=>()=>{const active=request.current;request.current=null;active?.abort();},[]);
  async function readLog(){
    if(request.current)return;
    const controller=new AbortController();request.current=controller;
    let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setLoading(true);setError("");
    try{
      const result=await untilAborted(managementCommand(service,"logs",{id},{signal:controller.signal}),controller.signal);
      if(!result || typeof result!=="object" || typeof result.log!=="string")throw new Error("작업 로그 응답 형식을 확인할 수 없습니다.");
      if(request.current===controller)setLog(result.log || "기록된 로그가 없습니다.");
    }catch(problem){
      if(request.current===controller)setError(timedOut ? "로그 조회 시간이 초과됐습니다. 다시 시도하세요." : requestErrorMessage(problem));
    }finally{
      clearTimeout(timeout);
      if(request.current===controller){request.current=null;setLoading(false);}
    }
  }
  return <><MediaJobResult service={service} kind="image" id={id}/>
    <button type="button" aria-disabled={loading} aria-describedby={loading ? statusId : error ? errorId : undefined} onClick={readLog}>{loading ? "로그 조회 중" : "실행 로그 조회"}</button>
    {loading && <p id={statusId} role="status">실행 로그를 불러오고 있습니다.</p>}
    {log!==null && (loading || error) && <p>아래는 마지막으로 조회한 로그입니다.</p>}
    {log!==null && <pre className="generator-job-log" tabIndex={0} role="region" aria-label="보관된 작업 실행 로그">{log}</pre>}{error && <p id={errorId} role="alert">{error}</p>}</>;
}

export default function QwenArchive(){
  const params=new URLSearchParams(location.search);
  const service=params.get("service")?.trim() || "",session=params.get("session");
  const [id,select]=useState(params.get("job") || "");
  const resultRef=useRef(null),historyRef=useRef(null),triggerRef=useRef(null),pendingFocus=useRef(false),focusEpoch=useRef(0);
  useEffect(()=>()=>{focusEpoch.current++;},[]);
  useEffect(()=>{
    if(!id || !pendingFocus.current)return;
    pendingFocus.current=false;
    if(document.activeElement===triggerRef.current || document.activeElement===document.body)resultRef.current?.focus();
  },[id]);
  function openResult(job){
    focusEpoch.current++;
    triggerRef.current=document.activeElement;
    history.replaceState(history.state,"",qwenArchiveUrl(location.href,job));
    if(id===job){resultRef.current?.focus();return;}
    pendingFocus.current=true;select(job);
  }
  function closeResult(){
    const epoch=++focusEpoch.current;
    history.replaceState(history.state,"",qwenArchiveUrl(location.href,""));
    pendingFocus.current=false;
    select("");
    requestAnimationFrame(()=>{if(epoch!==focusEpoch.current)return;if(!restoreLostFocus(document,triggerRef.current))restoreLostFocus(document,historyRef.current?.querySelector("summary"));});
  }
  async function readJob(job,{signal}={}){
    return readArchiveJob(managementCommand,service,job,{signal});
  }
  if(!service)return <main className="single-generator-shell"><article className="single-generator-page"><h1>Qwen 이미지 생성 이력</h1><p role="alert">보관 서비스가 지정되지 않았습니다. 헤르메스 대화로 돌아가 작업을 다시 여세요.</p><a href={"/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화로 돌아가기</a></article></main>;
  return <main className="single-generator-shell"><article className="single-generator-page"><a href={"/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화로 돌아가기</a>
    <h1>Qwen 이미지 생성 이력</h1><p>{service} · 보관된 작업</p>
    <GeneratorChangelog generator={service}/>
    <div ref={historyRef}><GeneratorHistory service={service} readJobWithSignal={readJob} openResult={openResult} externalResultId={id} emptyMessage="조회된 보관 이력이 없습니다. 검색 조건을 바꾸어 다시 조회하세요."/></div>
    {id && <section ref={resultRef} tabIndex={-1} aria-label="보관된 작업 결과" className="qwen-archive-result">
      <h2>보관된 작업 결과</h2><JobIdentifier id={id}/>
      <button type="button" onClick={closeResult}>결과 닫기</button>
      <ArchiveDetail key={id} service={service} id={id}/>
    </section>}
  </article></main>;
}
