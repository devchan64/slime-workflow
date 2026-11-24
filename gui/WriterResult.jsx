import React, {useEffect,useRef,useState} from "react";
import JobIdentifier from "./JobIdentifier.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {writerStageLabel} from "./writerLabels.mjs";
import {requestErrorMessage} from "./requestError.mjs";
import {LiveRefreshControl,useLiveRefresh} from "./LiveRefresh.jsx";
import ActionButton from "./ActionButton.jsx";

const activeStages=new Set(["queued","preparing","indexing","searching","reasoning"]);
const finishedStages=new Set(["review","completed","applied","failed","interrupted"]);

async function writerChange(command,payload){
  const controller=new AbortController();let timedOut=false;
  const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
  try{return await untilAborted(managementCommand("writer-agent",command,payload,{signal:controller.signal}),controller.signal);}
  catch(problem){if(timedOut)throw new Error("응답 시간이 초과됐습니다. 처리 여부를 확인해 주세요.");throw problem;}
  finally{clearTimeout(timer);}
}

export default function WriterResult(props) {
  return <WriterResultForJob key={props.id} {...props}/>;
}

function WriterResultForJob({id,onDeleted}) {
  const [detail,setDetail]=useState(null);
  const [error,setError]=useState("");
  const [checkedAt,setCheckedAt]=useState(null);
  const [checking,setChecking]=useState(true);
  const [revision,refresh]=useState(0);
  const [confirmed,setConfirmed]=useState(false);
  const [busy,setBusy]=useState(false);
  const [changeKind,setChangeKind]=useState("");
  const [deleteConfirmed,setDeleteConfirmed]=useState(false);
  const [notice,setNotice]=useState("");
  const [noticeError,setNoticeError]=useState(false);
  const followLog=useRef(true),refreshButton=useRef(null),applyButton=useRef(null),deleteButton=useRef(null),restoreRefreshFocus=useRef(false),changePending=useRef(false),readPending=useRef(true),requiresRead=useRef(true);
  useEffect(()=>{if(!checking && restoreRefreshFocus.current){restoreRefreshFocus.current=false;if(document.activeElement===document.body && !refreshButton.current?.disabled)refreshButton.current?.focus();}},[checking,busy]);
  const live=useLiveRefresh(()=>{if(!changePending.current && !readPending.current){readPending.current=true;setChecking(true);refresh(value=>value+1);}},!busy && (!detail || Boolean(error) || !finishedStages.has(detail.status.stage)));
  useEffect(()=>{setError("");setDetail(null);setCheckedAt(null);setConfirmed(false);setDeleteConfirmed(false);},[id]);
  useEffect(()=>{
    let active=true;
    const controller=new AbortController();
    let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    readPending.current=true;requiresRead.current=true;
    async function read() {
      setChecking(true);setConfirmed(false);setDeleteConfirmed(false);
      try {
        const record=await untilAborted(managementCommand("writer-agent","writer-detail",{id},{signal:controller.signal}),controller.signal);
        if(!active)return;
        if(!record || record.id!==id || typeof record.status?.stage!=="string" || !record.status.stage.trim() ||
          [record.status.error,record.status.summary,record.status.proposal_hash].some(value=>value!=null && typeof value!=="string") ||
          (record.proposal!=null && (typeof record.proposal!=="object" || Array.isArray(record.proposal) ||
            (record.proposal.reason!=null && typeof record.proposal.reason!=="string") ||
            (record.proposal.changes!=null && (!Array.isArray(record.proposal.changes) || record.proposal.changes.some(change=>!change || typeof change.path!=="string" || typeof change.diff!=="string"))))))
          throw new Error("선택한 작가 작업의 응답을 확인할 수 없습니다.");
        const updateLog=followLog.current;
        setDetail(previous=>previous && !updateLog ? {...record,log:previous.log} : record);
        requiresRead.current=false;
        setCheckedAt(new Date());
        setError("");
      } catch(problem) {
        if(!active)return;
        setError(timedOut ? "작업 결과 조회 시간이 초과됐습니다. 다시 확인하세요." : requestErrorMessage(problem));
        setConfirmed(false);setDeleteConfirmed(false);
      } finally {clearTimeout(timeout);if(active){readPending.current=false;setChecking(false);}}
    }
    read();
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[id,revision]);
  const proposal=detail?.proposal;
  const hash=detail?.status.proposal_hash;
  const canApply=!checking && !error && detail?.id===id && detail.status.stage==="review" && hash && proposal?.changes?.length>0 && !detail.application;
  async function apply() {
    if(!confirmed || !canApply || busy || changePending.current || readPending.current || requiresRead.current)return;
    changePending.current=true;
    restoreRefreshFocus.current=document.activeElement===applyButton.current;
    setBusy(true);setChangeKind("apply");setConfirmed(false);setNotice("");setNoticeError(false);
    try {
      const receipt=await writerChange("writer-apply",{id,proposal_hash:hash});
      const expected=proposal.changes.map(change=>change.path);
      if(receipt?.status!=="applied" || receipt.requires_learning!==true || !Array.isArray(receipt.paths) || receipt.paths.length!==expected.length || new Set(receipt.paths).size!==expected.length || receipt.paths.some(path=>typeof path!=="string" || !expected.includes(path)))throw new Error("적용 결과와 검토한 경로를 확인할 수 없습니다.");
      setNotice("검토한 변경을 적용했습니다. 다음 작업 전에 학습을 갱신하세요.");
    } catch(problem) {
      setNoticeError(true);setNotice("적용 요청 결과를 확인하세요. "+requestErrorMessage(problem));
    } finally {
      setDetail(null);readPending.current=true;setChecking(true);refresh(value=>value+1);changePending.current=false;setBusy(false);setChangeKind("");
    }
  }
  const canDelete=!checking && !error && detail?.id===id && finishedStages.has(detail.status.stage);
  async function trash() {
    if(busy || !canDelete || !deleteConfirmed || changePending.current || readPending.current || requiresRead.current)return;
    changePending.current=true;
    const restoreFocus=document.activeElement===deleteButton.current;
    setBusy(true);setChangeKind("delete");setDeleteConfirmed(false);setNotice("");setNoticeError(false);
    try {
      const receipt=await writerChange("writer-delete",{id});
      if(receipt.id!==id || receipt.status!=="deleted" || receipt.recoverable!==true)
        throw new Error("휴지통 이동 응답을 확인할 수 없습니다.");
      onDeleted(id,{restoreFocus});
    } catch(problem) {
      restoreRefreshFocus.current=restoreFocus;
      setNoticeError(true);setNotice("이력과 휴지통에서 처리 결과를 확인하세요. "+requestErrorMessage(problem));
      setDetail(null);readPending.current=true;setChecking(true);refresh(value=>value+1);
    } finally {changePending.current=false;setBusy(false);setChangeKind("");}
  }
  return <section ref={live.ref} className="writer-result" aria-label="작가 작업 결과"><h3>작업 결과</h3><JobIdentifier id={id}/>
    <button ref={refreshButton} disabled={busy || checking} onClick={()=>{if(changePending.current || readPending.current)return;readPending.current=true;restoreRefreshFocus.current=document.activeElement===refreshButton.current;setChecking(true);setConfirmed(false);setDeleteConfirmed(false);refresh(value=>value+1);}}>결과 새로고침</button>
    <LiveRefreshControl live={live} label="작업 상태 자동 갱신" inactiveReason={busy ? "변경 처리 중" : "작업 종료로 중지"}/>
    <label><input type="checkbox" defaultChecked onChange={event=>{followLog.current=event.target.checked;}}/>조회할 때 실행 로그 갱신</label>
    {busy && <p role="status">{changeKind==="apply" ? "원본 적용 요청 처리 중…" : "실행 기록 정리 요청 처리 중…"}</p>}
    {notice && <p role={noticeError ? "alert" : "status"}>{notice}</p>}
    {checkedAt && <p>마지막 조회 성공 · <time dateTime={checkedAt.toISOString()}>{checkedAt.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false})}</time></p>}
    {checking && detail && <p role="status">결과를 다시 조회하고 있습니다. 아래는 마지막 조회 결과입니다.</p>}
    {error && <p role="alert">{error}{detail && " 아래 내용은 마지막 조회 결과입니다. 재조회 전에는 적용과 삭제를 할 수 없습니다."}</p>}
    {!detail && !error && <p role="status">작업 결과를 조회하고 있습니다.</p>}
    {detail && <>
      <p role="status">{writerStageLabel(detail.status.stage)} · {detail.status.error || detail.status.summary || (typeof detail.status.progress==="object" ? JSON.stringify(detail.status.progress) : detail.status.progress)}</p>
      {!activeStages.has(detail.status.stage) && !finishedStages.has(detail.status.stage) && <p role="status">알 수 없는 작업 단계입니다. 상태를 다시 확인하세요.</p>}
      {proposal?.reason && <p>{proposal.reason}</p>}
      {proposal?.changes?.map(change=><details key={change.path}><summary>{change.path}</summary><pre tabIndex={0} aria-label={change.path+" 변경 내용"}>{change.diff}</pre></details>)}
      {canApply && <fieldset disabled={busy}><legend>원본 문서 적용</legend>
        <label><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>표시된 변경을 검토했고 원본 적용에 동의합니다.</label>
        <ActionButton buttonRef={applyButton} reasons={[!confirmed && "변경 내용을 검토하고 원본 적용 동의란을 선택하세요."]} onClick={apply}>확인한 변경을 원본에 적용</ActionButton>
      </fieldset>}
      {canDelete && <fieldset disabled={busy}><legend>실행 기록 정리</legend>
        <label><input type="checkbox" checked={deleteConfirmed} onChange={event=>setDeleteConfirmed(event.target.checked)}/>
          {id}의 입력·제안·로그를 휴지통으로 옮기는 데 동의합니다.</label>
        <ActionButton buttonRef={deleteButton} reasons={[!deleteConfirmed && "휴지통으로 옮길 기록을 확인하고 동의란을 선택하세요."]} onClick={trash}>실행 기록 휴지통으로 이동</ActionButton>
      </fieldset>}
      {Object.entries({"실행 입력":detail.request,"검토 범위":proposal?.coverage,"탐색 근거":proposal?.evidence,
        "경고":proposal?.warnings,"보존 판단":proposal?.retained,"적용 결과":detail.application,"검색 결과":detail.search,"실행 로그":detail.log})
        .filter(([,value])=>value!=null).map(([label,value])=><details key={label}><summary>{label}</summary>
          <pre tabIndex={0} aria-label={label}>{typeof value==="string"?value:JSON.stringify(value,null,2)}</pre></details>)}
    </>}
  </section>;
}
