import React, {useState} from "react";
import {managementCommand} from "./managementCommand.js";

export default function GeneratorHistory({service, statusCommand, restore}) {
  const [page,setPage]=useState(null);
  const [query,setQuery]=useState("");
  const [filter,setFilter]=useState("");
  const [job,setJob]=useState(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  async function load(operation) {
    setBusy(true); setError(""); setJob(null);
    try { await operation(); }
    catch(problem) { setError(problem.message); }
    finally { setBusy(false); }
  }
  async function list(offset, search) {
    const payload={limit:10,offset,query:search};
    if(offset)payload.snapshot=page.snapshot;
    const result=await managementCommand(service,"history-observe",payload);
    setPage(result);setFilter(search);
  }
  async function inspect(id) {
    const result=await managementCommand(service,statusCommand,{id});
    if(result.id!==id || !result.request)throw new Error("작업 입력을 확인할 수 없습니다.");
    setJob(result);
  }
  return <details><summary>생성 이력에서 입력 불러오기</summary>
    <fieldset disabled={busy}><label>작업 ID 검색 <input value={query} maxLength={80} onChange={e=>setQuery(e.target.value)}/></label>
      <button onClick={()=>load(()=>list(0,query.trim()))}>이력 조회</button>
      {page && <>
        <p>총 {page.total}건 · 이번 조회 {page.records.length}건</p>
        {page.records.map(record=><button key={record.id} onClick={()=>load(()=>inspect(record.id))}>
          {record.id} · {record.recorded_status}
        </button>)}
        <button disabled={!page.offset} onClick={()=>load(()=>list(Math.max(0,page.offset-10),filter))}>이전 이력 페이지</button>
        <button disabled={page.next_offset==null} onClick={()=>load(()=>list(page.next_offset,filter))}>다음 이력 페이지</button>
      </>}
      {job && <section><strong>{job.id}</strong><pre>{JSON.stringify(job.request,null,2)}</pre>
        <button onClick={()=>restore(job.request)}>이 작업의 입력으로 교체</button></section>}
    </fieldset>
    {error && <p role="alert">{error}</p>}
  </details>;
}
