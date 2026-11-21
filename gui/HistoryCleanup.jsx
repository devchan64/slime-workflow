import React, {useState} from "react";
import {formatCleanupResult} from "./formatCleanupResult.mjs";
import {managementCommand} from "./managementCommand.js";

export default function HistoryCleanup({service,job,state,onDeleted}) {
  const [review,setReview]=useState(null),[ack,setAck]=useState(false);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const eligible=["completed","failed","cancelled","paused"].includes(state);
  async function perform(operation) {
    setBusy(true);setNotice("");
    try {await operation();} catch(error){setNotice(error.message);}
    finally{setBusy(false);}
  }
  function reset() {setReview(null);setAck(false);}
  async function inspectAll() {
    reset();
    const preview=await managementCommand(service,"history-reset-preview",{});
    setReview({all:true,preview});
  }
  async function confirm() {
    if(!review || !ack)return;
    const target=review;
    reset();
    let result;
    if(target.all) {
      const current=await managementCommand(service,"history-reset-preview",{});
      if(!current.can_reset || JSON.stringify(current.jobs)!==JSON.stringify(target.preview.jobs))
        throw new Error("삭제 대상이 변경되었습니다. 다시 조회하세요.");
      result=await managementCommand(service,"history-reset",{action:"reset",expected_jobs:target.preview.jobs});
    } else {
      if(target.id!==job || !eligible)throw new Error("선택 작업의 상태가 변경되었습니다.");
      result=await managementCommand(service,"history-delete",{id:target.id});
    }
    onDeleted(formatCleanupResult(result));
  }
  return <details><summary>생성 이력 정리</summary>
    <fieldset disabled={busy}>
      <button disabled={!job || !eligible} onClick={()=>{setAck(false);setReview({id:job});}}>선택 이력 삭제 검토</button>
      <button onClick={()=>perform(inspectAll)}>전체 이력 삭제 대상 조회</button>
      {review && <section>
        <p>{review.all ? service+" · 전체 삭제 대상 "+review.preview.job_count+"건" : "선택 작업 · "+review.id}</p>
        <p>{review.all ? review.preview.scope : "작업 폴더의 입력 사본·결과·로그와 실행 기록을 삭제합니다."}</p>
        {review.all && <p>{review.preview.notice} · 삭제 제한 작업 {review.preview.blocked_jobs.length}건</p>}
        <label><input type="checkbox" checked={ack} onChange={e=>setAck(e.target.checked)}/>삭제 후 복구할 수 없음을 확인했습니다.</label>
        <button onClick={reset}>삭제 취소</button>
        <button disabled={!ack || (review.all && !review.preview.can_reset)} onClick={()=>perform(confirm)}>확인한 대상 삭제</button>
      </section>}
    </fieldset><p role="status">{notice}</p>
  </details>;
}
