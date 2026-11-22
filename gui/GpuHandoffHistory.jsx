import React,{useEffect,useRef,useState} from "react";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import {managementCommand} from "./managementCommand.js";
import {validateGpuHandoffStatus} from "./validateGpuHandoffStatus.mjs";

export default function GpuHandoffHistory({session}){
  const [rows,setRows]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [checkedAt,setCheckedAt]=useState(null);
  const activeRequest=useRef(null);
  async function refresh(){
    activeRequest.current?.abort();
    const controller=new AbortController();activeRequest.current=controller;
    let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    try{
      const result=await managementCommand("hermes-agent","hermes-gpu-handoff-list",{session_id:session},{signal:controller.signal});
      if(activeRequest.current!==controller || controller.signal.aborted)return;
      if(result.session_id!==session || !Array.isArray(result.handoffs) || result.handoffs.length>20)throw new Error("GPU 양도 이력 응답이 일치하지 않습니다.");
      const seen=new Set();
      for(const row of result.handoffs){
        if(!row || typeof row.id!=="string" || !/^[A-Za-z0-9_-]{8,80}$/.test(row.id) || typeof row.service!=="string" || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(row.service) || seen.has(row.id))throw new Error("GPU 양도 이력 형식 오류");
        validateGpuHandoffStatus(row,session,row.id,row.service);seen.add(row.id);
      }
      setRows(result.handoffs);setCheckedAt(new Date());
    }catch(problem){if(activeRequest.current===controller && (!controller.signal.aborted || timedOut))setError(timedOut?"GPU 양도 이력 조회 시간이 초과됐습니다. 다시 조회하세요.":problem instanceof TypeError?"GPU 양도 이력에 연결하지 못했습니다. 다시 조회하세요.":problem.message || "GPU 양도 이력을 확인할 수 없습니다.");}
    finally{clearTimeout(timer);if(activeRequest.current===controller){activeRequest.current=null;setBusy(false);}}
  }
  useEffect(()=>{setRows(null);setCheckedAt(null);refresh();return ()=>{activeRequest.current?.abort();activeRequest.current=null;};},[session]);
  return <section className="gpu-handoff-history" aria-label="GPU 양도 이력">
      <p>이 대화의 최근 양도 최대 20건을 최근 변경순으로 표시합니다.</p>
      <button type="button" disabled={busy} onClick={refresh}>{busy?"조회 중":"이력 새로고침"}</button>
      {checkedAt && <p>화면 수신 시각 · {checkedAt.toLocaleString("ko-KR")}</p>}
      {busy && <p role="status">GPU 양도 이력을 불러오는 중입니다.</p>}
      {error && <p role="alert">{error}</p>}
      {error && rows && <p>아래에는 마지막으로 조회한 이력이 표시됩니다.</p>}
      {rows && !rows.length && <p>{error ? "마지막 조회에서 이 대화의 양도 기록이 없었습니다." : "이 대화의 양도 기록이 없습니다."}</p>}
      {rows?.map(row=><GpuHandoffStatus key={row.id} session={session} id={row.id} service={row.service} status={row} onUpdate={value=>setRows(current=>current.map(item=>item.id===row.id?{...item,...value}:item))}><p>대상 · {row.service}</p><p>최근 변경 · {Number.isNaN(Date.parse(row.updated_at)) ? "확인 불가" : new Date(row.updated_at).toLocaleString("ko-KR")}</p></GpuHandoffStatus>)}
  </section>;
}
