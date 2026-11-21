import React, {useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

export default function AnchorHistory() {
  const [animation,setAnimation]=useState("");
  const [version,setVersion]=useState("");
  const [page,setPage]=useState(null);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);

  async function load(next) {
    const payload={animation_id:animation.trim(),animation_version:version.trim(),limit:20};
    if(next) Object.assign(payload,{offset:page.next_offset,snapshot:page.snapshot});
    setBusy(true);
    setError("");
    try {
      const result=await managementCommand("hermes-agent","hermes-anchor-history-observe",payload);
      const offset=payload.offset ?? 0;
      if(!Array.isArray(result.records) || result.offset!==offset ||
          !/^[a-f0-9]{64}$/.test(result.snapshot) || (next && result.snapshot!==payload.snapshot) ||
          (result.next_offset!==null && (result.next_offset!==offset+result.records.length || !result.records.length))) {
        throw new Error("이력이 변경되었거나 페이지 정보를 확인할 수 없습니다. 다시 조회하세요.");
      }
      setPage(result);
    } catch(problem) {
      setPage(null);
      setError(problem.message);
    } finally {
      setBusy(false);
    }
  }
  function edit(setter,value) {
    setter(value);
    setPage(null);
    setError("");
  }
  return <fieldset disabled={busy}><legend>과거 앵커 검수 이력</legend>
    <form onSubmit={event=>{event.preventDefault();load(false);}}>
      <label>애니메이션 ID<input required value={animation} onChange={e=>edit(setAnimation,e.target.value)}/></label>
      <label>애니메이션 버전<input required value={version} onChange={e=>edit(setVersion,e.target.value)}/></label>
      <button disabled={!animation.trim() || !version.trim()}>이력 조회</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {page && <ResultTable table={{title:"과거 좌표 검수 기록",summary:"전체 "+page.total+"건",
      columns:["이력 ID","저장 시각","프레임 수"],rows:page.records.map(row=>[row.id,row.created_at,row.frames])}}/>}
    {page?.next_offset!=null && <button onClick={()=>load(true)}>다음 이력</button>}
  </fieldset>;
}
