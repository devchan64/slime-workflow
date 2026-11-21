import React, {useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";

const activeStages=new Set(["queued","preparing","indexing","searching","reasoning"]);

export default function WriterResult({id,onDeleted}) {
  const [detail,setDetail]=useState(null);
  const [error,setError]=useState("");
  const [revision,refresh]=useState(0);
  const [confirmed,setConfirmed]=useState(false);
  const [busy,setBusy]=useState(false);
  const [deleteConfirmed,setDeleteConfirmed]=useState(false);
  const [notice,setNotice]=useState("");
  const followLog=useRef(true);
  useEffect(()=>{
    let active=true,timer;
    setError("");setDetail(null);setConfirmed(false);setDeleteConfirmed(false);
    async function read() {
      try {
        const record=await managementCommand("writer-agent","writer-detail",{id});
        if(!active)return;
        if(record.id!==id || !record.status?.stage)throw new Error("선택한 작가 작업과 조회 결과가 일치하지 않습니다.");
        const updateLog=followLog.current;
        setDetail(previous=>previous && !updateLog ? {...record,log:previous.log} : record);
        setError("");
        if(activeStages.has(record.status.stage))timer=setTimeout(read,3000);
      } catch(problem) {
        if(!active)return;
        setError(problem.message);
        setDetail(null);
        timer=setTimeout(read,3000);
      }
    }
    read();
    return ()=>{active=false;clearTimeout(timer);};
  },[id,revision]);
  const proposal=detail?.proposal;
  const hash=detail?.status.proposal_hash;
  const canApply=detail?.id===id && detail.status.stage==="review" && hash && proposal?.changes?.length>0 && !detail.application;
  async function apply() {
    if(!confirmed || !canApply || busy)return;
    setBusy(true);setConfirmed(false);setNotice("");
    try {
      await managementCommand("writer-agent","writer-apply",{id,proposal_hash:hash});
      setNotice("검토한 변경을 적용했습니다.");
    } catch(problem) {
      setNotice("적용 요청 결과를 확인하세요. "+problem.message);
    } finally {
      setDetail(null);refresh(value=>value+1);setBusy(false);
    }
  }
  const canDelete=detail?.id===id && Boolean(detail.status.stage) &&
    !activeStages.has(detail.status.stage);
  async function trash() {
    if(busy || !canDelete || !deleteConfirmed)return;
    setBusy(true);setDeleteConfirmed(false);setNotice("");
    try {
      const receipt=await managementCommand("writer-agent","writer-delete",{id});
      if(receipt.id!==id || receipt.status!=="deleted" || receipt.recoverable!==true)
        throw new Error("휴지통 이동 응답을 확인할 수 없습니다.");
      onDeleted(id);
    } catch(problem) {
      setNotice("이력과 휴지통에서 처리 결과를 확인하세요. "+problem.message);
      setDetail(null);refresh(value=>value+1);
    } finally {setBusy(false);}
  }
  return <section aria-label="작가 작업 결과"><h3>{id}</h3>
    <button disabled={busy} onClick={()=>{setConfirmed(false);refresh(value=>value+1);}}>결과 새로고침</button>
    <label><input type="checkbox" defaultChecked onChange={event=>{followLog.current=event.target.checked;}}/>실행 로그 자동 갱신</label>
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
    {detail && <>
      <p role="status">{detail.status.stage} · {detail.status.error || detail.status.summary || (typeof detail.status.progress==="object" ? JSON.stringify(detail.status.progress) : detail.status.progress)}</p>
      {proposal?.reason && <p>{proposal.reason}</p>}
      {proposal?.changes?.map(change=><details key={change.path}><summary>{change.path}</summary><pre>{change.diff}</pre></details>)}
      {canApply && <fieldset disabled={busy}><legend>원본 문서 적용</legend>
        <label><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>표시된 변경을 검토했고 원본 적용에 동의합니다.</label>
        <button disabled={!confirmed} onClick={apply}>확인한 변경을 원본에 적용</button>
      </fieldset>}
      {canDelete && <fieldset disabled={busy}><legend>실행 기록 정리</legend>
        <label><input type="checkbox" checked={deleteConfirmed} onChange={event=>setDeleteConfirmed(event.target.checked)}/>
          {id}의 입력·제안·로그를 휴지통으로 옮기는 데 동의합니다.</label>
        <button disabled={!deleteConfirmed} onClick={trash}>실행 기록 휴지통으로 이동</button>
      </fieldset>}
      {Object.entries({"실행 입력":detail.request,"검토 범위":proposal?.coverage,"탐색 근거":proposal?.evidence,
        "경고":proposal?.warnings,"보존 판단":proposal?.retained,"적용 결과":detail.application,"검색 결과":detail.search,"실행 로그":detail.log})
        .filter(([,value])=>value!=null).map(([label,value])=><details key={label}><summary>{label}</summary>
          <pre>{typeof value==="string"?value:JSON.stringify(value,null,2)}</pre></details>)}
    </>}
  </section>;
}
