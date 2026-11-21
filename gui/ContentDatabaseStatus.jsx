import MapDatabaseReceipt from "./MapDatabaseReceipt.jsx";
import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

export default function ContentDatabaseStatus(){
  const [record,setRecord]=useState(null),[error,setError]=useState(""),[revision,refresh]=useState(0);
  useEffect(()=>{
    let active=true;
    setRecord(null);setError("");
    managementCommand("hermes-agent","hermes-content-database-status").then(result=>{
      if(active)setRecord(result);
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[revision]);
  const available=record?.status==="available",sources=record?.map_sources,save=record?.map_save;
  const rows=record?[
    ["콘텐츠 DB",available?"연결됨":"확인 불가"],
    ...(available?[
      ["DB 저장 세대",record.generation],["원장 반영 세대",record.ledger_generation],
      ["반영 대기",record.pending?"예":"아니요"],
      ["최근 반영",record.latest?record.latest.state+(record.latest.lease_expired?" · 임대 만료":""):"기록 없음"]
    ]:[]),
    ["헤르메스 맵 모드",({files:"파일",database:"DB"})[record.local_map_mode] || "확인 불가"],
    ["원본·등록부·백엔드 잠금",({matched:"일치",mismatch:"불일치"})[sources?.status] || "확인 불가"],
    ...(Number.isInteger(sources?.checked_files)?[["검사 파일",sources.checked_files],["불일치 파일",sources.mismatched_files]]:[]),
    ["야외 맵 저장",({clear:"중단 기록 없음",busy:"진행 중",pending:"중단 기록 확인 필요"})[save?.state] || "확인 불가"]
  ]:[];
  return <section>
    <button disabled={!record&&!error} onClick={()=>refresh(n=>n+1)}>콘텐츠 DB 상태 새로고침</button>
    {error && <p role="alert">{error}</p>}
    {record?<><ResultTable table={{title:"콘텐츠 DB와 원장",summary:record.queried_at,columns:["항목","조회 결과"],rows}}/>
      <p>{record.note}</p>
      {save?.state==="pending" && Array.isArray(save.file_details) && <ResultTable table={{
        title:"맵 저장 중단 파일",summary:"현재 파일과 백업 상태",columns:["경로","현재","백업"],
        rows:save.file_details.map(file=>[file.path,file.current,file.backup])}}/>}
    </>:!error && <p role="status">콘텐츠 DB 상태 조회 중…</p>}
    <MapDatabaseReceipt/>
  </section>;
}
