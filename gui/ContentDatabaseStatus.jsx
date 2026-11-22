import MapDatabaseReceipt from "./MapDatabaseReceipt.jsx";
import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

export default function ContentDatabaseStatus(){
  const [record,setRecord]=useState(null),[error,setError]=useState(""),[revision,refresh]=useState(0);
  const [loading,setLoading]=useState(true),[receivedAt,setReceivedAt]=useState(null);
  useEffect(()=>{
    let active=true;
    setLoading(true);setError("");
    managementCommand("hermes-agent","hermes-content-database-status").then(result=>{
      if(!result || !["available","unavailable"].includes(result.status))throw new Error("콘텐츠 DB 상태 형식을 확인할 수 없습니다.");
      if(active){setRecord(result);setReceivedAt(new Date());}
    }).catch(problem=>{if(active)setError(problem instanceof TypeError?"콘텐츠 DB 상태에 연결하지 못했습니다. 다시 시도하세요.":problem.message);}).finally(()=>{if(active)setLoading(false);});
    return ()=>{active=false;};
  },[revision]);
  const available=record?.status==="available",sources=record?.map_sources,save=record?.map_save;
  const observedAt=record?.queried_at && !Number.isNaN(Date.parse(record.queried_at)) ? new Date(record.queried_at).toLocaleString("ko-KR") : "확인 불가";
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
    <button disabled={loading} onClick={()=>refresh(n=>n+1)}>{loading?"조회 중…":"콘텐츠 DB 상태 새로고침"}</button>
    {error && <p role="alert">{error}{record && " 이전 조회 결과를 유지합니다."}</p>}
    {loading && record && <p role="status">새 상태 조회 중 · 아래는 이전 결과입니다.</p>}
    {record?<><p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p><ResultTable table={{title:"콘텐츠 DB와 원장",summary:"서버 관측 시각 · "+observedAt,columns:["항목","조회 결과"],rows}}/>
      <p>{record.note}</p>
      {save?.state==="pending" && Array.isArray(save.file_details) && <ResultTable table={{
        title:"맵 저장 중단 파일",summary:"현재 파일과 백업 상태",columns:["경로","현재","백업"],
        rows:save.file_details.map(file=>[file.path,file.current,file.backup])}}/>}
    </>:!error && <p role="status">콘텐츠 DB 상태 조회 중…</p>}
    <MapDatabaseReceipt/>
  </section>;
}
