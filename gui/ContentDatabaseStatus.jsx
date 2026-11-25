import MapDatabaseReceipt from "./MapDatabaseReceipt.jsx";
import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ResultTable from "./ResultTable.jsx";

const mapModeLabels=new Map([["files","파일"],["database","DB"]]);
const sourceLabels=new Map([["matched","일치"],["mismatch","불일치"]]);
const saveLabels=new Map([["clear","중단 기록 없음"],["busy","진행 중"],["pending","중단 기록 확인 필요"]]);
const contentLabelGroups=new Map([["mode",mapModeLabels],["source",sourceLabels],["save",saveLabels]]);
export function contentStatusLabel(kind,value){
  return contentLabelGroups.get(kind)?.get(value) || "확인 불가";
}

function validContentStatus(result){
  if(!result || !["available","unavailable"].includes(result.status) || (result.note!=null && typeof result.note!=="string"))return false;
  if(result.status==="available" && (!Number.isInteger(result.generation) || result.generation<0 || !Number.isInteger(result.ledger_generation) || result.ledger_generation<0 || result.ledger_generation>result.generation || typeof result.pending!=="boolean" || result.pending!==(result.generation>result.ledger_generation) || (result.latest!=null && (typeof result.latest.state!=="string" || typeof result.latest.lease_expired!=="boolean"))))return false;
  if(result.map_sources?.checked_files!=null && (!Number.isSafeInteger(result.map_sources.checked_files) || result.map_sources.checked_files<0 || !Number.isSafeInteger(result.map_sources.mismatched_files) || result.map_sources.mismatched_files<0 || result.map_sources.mismatched_files>result.map_sources.checked_files))return false;
  if(["matched","mismatch"].includes(result.map_sources?.status) && (!Number.isSafeInteger(result.map_sources.checked_files) || !Number.isSafeInteger(result.map_sources.mismatched_files) || (result.map_sources.status==="matched")!==(result.map_sources.mismatched_files===0)))return false;
  if(result.map_save?.file_details!=null && (!Array.isArray(result.map_save.file_details) || result.map_save.file_details.some(file=>!file || ![file.path,file.current,file.backup].every(value=>typeof value==="string"))))return false;
  return true;
}

export default function ContentDatabaseStatus(){
  const loadingId=useId();
  const [record,setRecord]=useState(null),[error,setError]=useState(""),[revision,refresh]=useState(0);
  const [loading,setLoading]=useState(true),[receivedAt,setReceivedAt]=useState(null);
  const refreshRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>{if(!loading && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)refreshRef.current?.focus();}},[loading]);
  useEffect(()=>{
    let active=true;
    const controller=new AbortController();let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setLoading(true);setError("");
    untilAborted(managementCommand("hermes-agent","hermes-content-database-status",{},{signal:controller.signal}),controller.signal).then(result=>{
      if(!validContentStatus(result))throw new Error("콘텐츠 DB 상태 형식을 확인할 수 없습니다.");
      if(active && !controller.signal.aborted){setRecord(result);setReceivedAt(new Date());}
    }).catch(problem=>{if(active)setError(timedOut?"콘텐츠 DB 상태 조회 시간이 초과됐습니다. 다시 시도하세요.":requestErrorMessage(problem));}).finally(()=>{clearTimeout(timer);if(active)setLoading(false);});
    return ()=>{active=false;clearTimeout(timer);controller.abort();};
  },[revision]);
  const available=record?.status==="available",sources=record?.map_sources,save=record?.map_save;
  const observedTime=record?.queried_at ? Date.parse(record.queried_at) : NaN;
  const observedAt=Number.isFinite(observedTime) ? new Date(observedTime).toLocaleString("ko-KR") : "확인 불가";
  const showObservedTime=!Number.isFinite(observedTime) || !receivedAt || Math.abs(receivedAt.getTime()-observedTime)>30000;
  const rows=record?[
    ["콘텐츠 DB",available?"연결됨":"확인 불가"],
    ...(available?[
      ["DB 저장 세대",record.generation],["원장 반영 세대",record.ledger_generation],
      ["반영 대기",record.pending?"예":"아니요"],
      ["최근 반영",record.latest?record.latest.state+(record.latest.lease_expired?" · 임대 만료":""):"기록 없음"]
    ]:[]),
    ["헤르메스 맵 모드",contentStatusLabel("mode",record.local_map_mode)],
    ["원본·등록부·백엔드 잠금",contentStatusLabel("source",sources?.status)],
    ...(Number.isInteger(sources?.checked_files)?[["검사 파일",sources.checked_files],["불일치 파일",sources.mismatched_files]]:[]),
    ["야외 맵 저장",contentStatusLabel("save",save?.state)]
  ]:[];
  return <section>
    <button ref={refreshRef} disabled={loading} aria-describedby={loading ? loadingId : undefined} onClick={()=>{restoreFocus.current=true;setLoading(true);refresh(n=>n+1);}}>{loading?"조회 중…":"콘텐츠 DB 상태 새로고침"}</button>
    {error && <p role="alert">{error}{record && " 이전 조회 결과를 유지합니다."}</p>}
    {loading && <p id={loadingId} role="status">{record ? "새 상태 조회 중 · 아래는 이전 결과입니다." : "콘텐츠 DB 상태 조회 중…"}</p>}
    {record?<><p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p><ResultTable table={{title:"콘텐츠 DB와 원장",summary:showObservedTime ? "서버 관측 시각 · "+observedAt : undefined,columns:["항목","조회 결과"],rows}}/>
      <p>{record.note}</p>
      {save?.state==="pending" && Array.isArray(save.file_details) && <ResultTable table={{
        title:"맵 저장 중단 파일",summary:"현재 파일과 백업 상태",columns:["경로","현재","백업"],
        rows:save.file_details.map(file=>[file.path,file.current,file.backup])}}/>}
    </>:null}
    <MapDatabaseReceipt/>
  </section>;
}
