import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {readBuildingSessionReceipts} from "./buildingProposalProtocol.mjs";
import ResultTable from "./ResultTable.jsx";
import JobIdentifier from "./JobIdentifier.jsx";

export default function BuildingSessionReceipts({session}){
  const [page,setPage]=useState(null),[rows,setRows]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [checkedAt,setCheckedAt]=useState(null),[stale,setStale]=useState(false);
  async function load(offset=0,snapshot){
    setBusy(true);setError("");
    try{
      const result=await readBuildingSessionReceipts(managementCommand,session,offset,snapshot);
      setRows(result.rows);setPage(result.page);setCheckedAt(new Date());setStale(false);
    }catch(problem){setStale(true);setError((problem.message || "대화 접수 이력을 확인할 수 없습니다.")+(page ? " 이전 조회 결과를 표시합니다. 다시 조회하세요." : ""));}
    finally{setBusy(false);}
  }
  return <section aria-label="대화 에셋 변경 접수"><h3>대화 에셋 변경 접수</h3>
    {!session ? <p>대화를 선택하면 접수 기록을 확인할 수 있습니다.</p> : <button type="button" disabled={busy} onClick={()=>load()}>현재 대화 접수 조회</button>}
    {busy && <p role="status">대화 접수 이력을 조회하고 있습니다.</p>}
    {error && <p role="alert">{error}</p>}
    {page && <><p>조회 시각 · {checkedAt?.toLocaleString("ko-KR")}{stale && " · 이전 결과"}</p><ResultTable table={{title:"에셋 변경 접수",summary:"현재 대화 페이지의 접수 "+rows.length+"건",columns:["대화 작업 ID","접수 상태","GPU"],rows:rows.map(([id,...cells])=>[id && id!=="확인 불가" ? <JobIdentifier id={id} compact/> : id,...cells])}}/>
      {page.offset>0 && <button type="button" disabled={busy || stale} onClick={()=>load(Math.max(0,page.offset-6),page.snapshot)}>최근 대화</button>}
      {page.next_offset!=null && <button type="button" disabled={busy || stale} onClick={()=>load(page.next_offset,page.snapshot)}>이전 대화</button>}</>}
  </section>;
}
