import React, {useEffect, useState} from "react";
import {requestErrorMessage} from "./requestError.mjs";
import {downloadPollInterval} from "./downloadPollInterval.mjs";

export default function DownloadProgress({service}) {
  const [lines, setLines] = useState(null);
  const [error, setError] = useState("");
  const [checkedAt,setCheckedAt]=useState(null);
  useEffect(() => {
    setLines(null);setCheckedAt(null);setError("");
    const controller = new AbortController();
    let timer;
    async function read() {
      let interval=downloadPollInterval(false);
      try {
        const response = await fetch("/management/assistant/model-downloads/" + encodeURIComponent(service), {signal:controller.signal, cache:"no-store"});
        if (!response.ok) throw new Error("다운로드 기록을 조회할 수 없습니다.");
        const data = await response.json();
        if (!Array.isArray(data.lines) || data.lines.some(line=>typeof line!=="string")) throw new Error("다운로드 기록 응답을 확인할 수 없습니다.");
        interval=downloadPollInterval(data.active);
        if (!controller.signal.aborted) {
          setLines(data.lines);
          setCheckedAt(new Date());
          setError("");
        }
      } catch (problem) {
        if (!controller.signal.aborted) setError(requestErrorMessage(problem));
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(read, interval);
      }
    }
    read();
    return () => {controller.abort(); clearTimeout(timer);};
  }, [service]);
  return <section className="download-progress"><h2>다운로드 진행 상황</h2>
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {error && <p role="alert">{error} 잠시 후 다시 확인합니다.{lines!==null && " 아래는 마지막 조회 결과입니다."}</p>}
    {lines === null ? !error &&
      <p role="status">다운로드 기록 조회 중…</p> : lines.length ?
      <ul>{lines.map((line, index) => <li key={index}>{line}</li>)}</ul> :
      <p role="status">진행 중인 다운로드와 최근 결과가 없습니다.</p>}
  </section>;
}
