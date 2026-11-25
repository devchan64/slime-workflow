import React, {useEffect, useId, useRef, useState} from "react";
import {untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import {downloadPollInterval} from "./downloadPollInterval.mjs";
import {LiveRefreshControl,useLiveRefresh} from "./LiveRefresh.jsx";

export default function DownloadProgress({service}) {
  return <DownloadProgressForService key={service} service={service}/>;
}

function DownloadProgressForService({service}) {
  const checkingId=useId();
  const [lines, setLines] = useState(null);
  const [error, setError] = useState("");
  const [checkedAt,setCheckedAt]=useState(null);
  const [downloading,setDownloading]=useState(false);
  const [checking,setChecking]=useState(true),[revision,setRevision]=useState(0);
  const pending=useRef(true);
  function refreshProgress(){
    if(pending.current)return;
    pending.current=true;setChecking(true);setRevision(value=>value+1);
  }
  const live=useLiveRefresh(refreshProgress,true,downloadPollInterval(downloading && !error));
  useEffect(() => {setLines(null);setCheckedAt(null);setError("");setDownloading(false);}, [service]);
  useEffect(() => {
    let active=true,controller;
    async function read() {
      if(!active)return;
      pending.current=true;
      controller=new AbortController();
      let timedOut=false;
      const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      if(active)setChecking(true);
      try {
        const data = await untilAborted((async()=>{
          const response = await fetch("/management/assistant/model-downloads/" + encodeURIComponent(service), {signal:controller.signal, cache:"no-store"});
          if (!response.ok) throw new Error("다운로드 기록을 조회할 수 없습니다.");
          return response.json();
        })(),controller.signal);
        if (!data || typeof data.active!=="boolean" || !Array.isArray(data.lines) || data.lines.some(line=>typeof line!=="string")) throw new Error("다운로드 기록 응답을 확인할 수 없습니다.");
        if (active) {
          setLines(data.lines);
          setDownloading(data.active);
          setCheckedAt(new Date());
          setError("");
        }
      } catch (problem) {
        if (active) setError(timedOut ? "다운로드 기록 조회 시간이 초과됐습니다." : requestErrorMessage(problem));
      } finally {
        clearTimeout(timeout);
        if (active) {pending.current=false;setChecking(false);}
      }
    }
    read();
    return () => {active=false;controller?.abort();};
  }, [service,revision]);
  const stale=Boolean(error || checking);
  return <section className="download-progress" ref={live.ref}><h2>다운로드 진행 상황</h2>
    <button type="button" aria-disabled={checking} aria-describedby={checking ? checkingId : undefined} onClick={refreshProgress}>{checking ? "다운로드 기록 조회 중…" : "다운로드 기록 새로고침"}</button>
    <LiveRefreshControl live={live} label="다운로드 기록 자동 갱신"/>
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {checking && <p id={checkingId} role="status">{lines===null ? "다운로드 기록을 확인하고 있습니다." : "다운로드 기록을 다시 확인하고 있습니다. 아래는 마지막 조회 결과입니다."}</p>}
    {error && <p role="alert">{error} 새로고침으로 다시 확인하세요.{lines!==null && " 아래는 마지막 조회 결과입니다."}</p>}
    {downloading && lines?.length>0 && <p role="status">{stale ? "마지막 조회 당시 다운로드 진행 중" : "다운로드 진행 중"}</p>}
    {lines === null ? null : lines.length ?
      <ul>{lines.map((line, index) => <li key={index}>{line}</li>)}</ul> :
      <p role="status">{downloading ? (stale ? "마지막 조회 당시 다운로드 진행 중 · 기록 없음" : "다운로드가 진행 중이며 기록을 기다리고 있습니다.") : (stale ? "마지막 조회 당시 진행 중인 다운로드와 최근 결과가 없었습니다." : "진행 중인 다운로드와 최근 결과가 없습니다.")}</p>}
  </section>;
}
