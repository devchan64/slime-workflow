import React, {useEffect, useState} from "react";
import ResultTable from "./ResultTable.jsx";

export default function CapabilitySearch({search, choose}) {
  const [catalog, setCatalog] = useState(null);
  const [error, setError] = useState("");
  const [revision, refresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch("/management/assistant/capabilities", {signal:controller.signal});
        if (!response.ok) throw new Error("관리 기능을 조회할 수 없습니다.");
        const record = await response.json();
        if (!controller.signal.aborted) {setCatalog(record); setError("");}
      } catch (problem) {
        if (!controller.signal.aborted) setError(problem.message);
      }
    }
    load();
    return () => controller.abort();
  }, [revision]);
  const query = search.trim().toLowerCase();
  const rows = catalog?.rows.filter(row => row.join(" ").toLowerCase().includes(query)) || [];
  return <>
    <button onClick={() => refresh(value => value + 1)}>관리 기능 새로고침</button>
    {error && <p role="alert">{error}</p>}
    {catalog ? <ResultTable table={{
      title:"관리 기능", summary:rows.length+"개 검색됨 · "+catalog.summary,
      columns:["기능","명령","연결","입력","영향","GPU","재시도","확인 사항"],
      rows:rows.map(([label,command,...fields]) => [
        <button onClick={() => choose(label,command)}>{label}</button>,command,...fields,
      ]),
    }}/> : !error && <p role="status">관리 기능 조회 중…</p>}
  </>;
}
