import React, {useEffect, useState} from "react";
import {requestErrorMessage} from "./requestError.mjs";
import {downloadPollInterval} from "./downloadPollInterval.mjs";

export default function DownloadProgress({service}) {
  const [lines, setLines] = useState(null);
  const [error, setError] = useState("");
  const [checkedAt,setCheckedAt]=useState(null);
  const [downloading,setDownloading]=useState(false);
  const [checking,setChecking]=useState(false),[revision,setRevision]=useState(0);
  useEffect(() => {setLines(null);setCheckedAt(null);setError("");setDownloading(false);}, [service]);
  useEffect(() => {
    let active=true,timer,controller;
    async function read() {
      let interval=downloadPollInterval(false);
      controller=new AbortController();
      let timedOut=false;
      const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      if(active)setChecking(true);
      try {
        const response = await fetch("/management/assistant/model-downloads/" + encodeURIComponent(service), {signal:controller.signal, cache:"no-store"});
        if (!response.ok) throw new Error("다운로드 기록을 조회할 수 없습니다.");
        const data = await response.json();
        if (!data || typeof data.active!=="boolean" || !Array.isArray(data.lines) || data.lines.some(line=>typeof line!=="string")) throw new Error("다운로드 기록 응답을 확인할 수 없습니다.");
        interval=downloadPollInterval(data.active);
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
        if (active) {setChecking(false);timer = setTimeout(read, interval);}
      }
    }
    read();
    return () => {active=false;controller?.abort(); clearTimeout(timer);};
  }, [service,revision]);
  return <section className="download-progress"><h2>다운로드 진행 상황</h2>
    <button type="button" disabled={checking} onClick={()=>setRevision(value=>value+1)}>{checking ? "다운로드 기록 조회 중…" : "다운로드 기록 새로고침"}</button>
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {error && <p role="alert">{error} 잠시 후 다시 확인합니다.{lines!==null && " 아래는 마지막 조회 결과입니다."}</p>}
    {downloading && lines?.length>0 && <p role="status">{error ? "마지막 조회 당시 다운로드 진행 중" : "다운로드 진행 중"}</p>}
    {lines === null ? null : lines.length ?
      <ul>{lines.map((line, index) => <li key={index}>{line}</li>)}</ul> :
      <p role="status">{downloading ? (error ? "마지막 조회 당시 다운로드 진행 중 · 기록 없음" : "다운로드가 진행 중이며 기록을 기다리고 있습니다.") : (error ? "마지막 조회 당시 진행 중인 다운로드와 최근 결과가 없었습니다." : "진행 중인 다운로드와 최근 결과가 없습니다.")}</p>}
  </section>;
}
