import React, {useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";

export default function WriterResult({id}) {
  const [detail,setDetail]=useState(null);
  const [error,setError]=useState("");
  const [revision,refresh]=useState(0);
  const [confirmed,setConfirmed]=useState(false);
  const [applying,setApplying]=useState(false);
  const [notice,setNotice]=useState("");
  useEffect(()=>{
    let active=true;
    setError("");setDetail(null);setConfirmed(false);
    managementCommand("writer-agent","writer-detail",{id}).then(record=>{
      if(record.id!==id)throw new Error("선택한 작가 작업과 조회 결과가 일치하지 않습니다.");
      if(active)setDetail(record);
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[id,revision]);
  const proposal=detail?.proposal;
  const hash=detail?.status.proposal_hash;
  const canApply=detail?.id===id && detail.status.stage==="review" && hash && proposal?.changes?.length>0 && !detail.application;
  async function apply() {
    if(!confirmed || !canApply || applying)return;
    setApplying(true);setConfirmed(false);setNotice("");
    try {
      await managementCommand("writer-agent","writer-apply",{id,proposal_hash:hash});
      setNotice("검토한 변경을 적용했습니다.");
    } catch(problem) {
      setNotice("적용 요청 결과를 확인하세요. "+problem.message);
    } finally {
      setDetail(null);refresh(value=>value+1);setApplying(false);
    }
  }
  return <section aria-label="작가 작업 결과"><h3>{id}</h3>
    <button disabled={applying} onClick={()=>{setConfirmed(false);refresh(value=>value+1);}}>결과 새로고침</button>
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
    {detail && <>
      <p role="status">{detail.status.stage} · {detail.status.error || detail.status.summary}</p>
      {proposal?.reason && <p>{proposal.reason}</p>}
      {proposal?.changes?.map(change=><details key={change.path}><summary>{change.path}</summary><pre>{change.diff}</pre></details>)}
      {canApply && <fieldset disabled={applying}><legend>원본 문서 적용</legend>
        <label><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>표시된 변경을 검토했고 원본 적용에 동의합니다.</label>
        <button disabled={!confirmed} onClick={apply}>확인한 변경을 원본에 적용</button>
      </fieldset>}
      {Object.entries({"실행 입력":detail.request,"검토 범위":proposal?.coverage,"탐색 근거":proposal?.evidence,
        "경고":proposal?.warnings,"보존 판단":proposal?.retained,"적용 결과":detail.application,"검색 결과":detail.search,"실행 로그":detail.log})
        .filter(([,value])=>value!=null).map(([label,value])=><details key={label}><summary>{label}</summary>
          <pre>{typeof value==="string"?value:JSON.stringify(value,null,2)}</pre></details>)}
    </>}
  </section>;
}
