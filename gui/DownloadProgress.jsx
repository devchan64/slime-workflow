import React, {useEffect, useState} from "react";

export default function DownloadProgress({service}) {
  const [lines, setLines] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let timer;
    async function read() {
      try {
        const response = await fetch("/management/assistant/model-downloads/" + encodeURIComponent(service), {signal:controller.signal, cache:"no-store"});
        if (!response.ok) throw new Error("다운로드 기록을 조회할 수 없습니다.");
        const data = await response.json();
        if (!controller.signal.aborted) {
          setLines(data.lines);
          setError("");
        }
      } catch (problem) {
        if (!controller.signal.aborted) setError(problem.message);
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(read, 5000);
      }
    }
    read();
    return () => {controller.abort(); clearTimeout(timer);};
  }, [service]);
  return <section><h2>다운로드 진행 상황</h2>
    {error ? <p role="alert">{error}</p> : lines.length ?
      <ul>{lines.map((line, index) => <li key={index}>{line}</li>)}</ul> :
      <p role="status">다운로드 기록 조회 중…</p>}
  </section>;
}
