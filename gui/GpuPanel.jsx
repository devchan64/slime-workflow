import React, {useEffect, useRef, useState} from "react";
import JobIdentifier from "./JobIdentifier.jsx";
import {LiveRefreshControl, useLiveRefresh} from "./LiveRefresh.jsx";

function memory(value) {
  return Number.isInteger(value) && value >= 0 ? value.toLocaleString() + " MiB" : "미측정";
}
function memoryPercent(used,total) {
  return Number.isFinite(used) && Number.isFinite(total) && used >= 0 && total > 0 && used <= total ? (used / total * 100).toFixed(1) + "%" : null;
}

function processJobLink(process) {
  const pages={"Wan2.2 VACE":"wan22-vace-generator","Wan2.2 Fun Control":"wan22-fun-control-generator","Kimodo 모션·SOMA 렌더":"kimodo-generator","헤르메스 작업":"hermes-agent"};
  const page=pages[process.command];
  if(!page || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(process.id || ""))return null;
  const parameters=new URLSearchParams({job:process.id});
  if(page==="hermes-agent")parameters.set("panel","jobs");
  const session=new URLSearchParams(location.search).get("session");
  if(session && /^[a-f0-9]{32}$/.test(session))parameters.set("session",session);
  return `/management/frame/${page}/?${parameters}`;
}

export default function GpuPanel({embedded=false}) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [checkedAt,setCheckedAt]=useState(null),[revision,setRevision]=useState(0),[loading,setLoading]=useState(true);
  const live=useLiveRefresh(()=>setRevision(value=>value+1));
  const refreshRef=useRef(null),restoreRefreshFocus=useRef(false);
  useEffect(()=>{if(!loading && restoreRefreshFocus.current){restoreRefreshFocus.current=false;if(document.activeElement===document.body)refreshRef.current?.focus();}},[loading]);
  useEffect(() => {
    const controller = new AbortController();
    async function refresh() {
      setLoading(true);
      try {
        const response = await fetch("/management/gpu-status", {cache:"no-store",signal:controller.signal});
        if (!response.ok) throw new Error("GPU 상태 조회 실패");
        const next = await response.json();
        if (!controller.signal.aborted) {setStatus(next);setCheckedAt(new Date());setError("");}
      } catch (problem) {
        if (!controller.signal.aborted) setError(problem instanceof TypeError ? "GPU 상태에 연결하지 못했습니다. 다시 조회하세요." : problem.message);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    refresh();
    return () => controller.abort();
  }, [revision]);
  const processes = Array.isArray(status?.processes) ? status.processes : null;
  const domains = ["vram","gtt"].filter(domain=>status?.[domain+"_total_mib"] != null);
  const vramPercent=memoryPercent(status?.vram_used_mib,status?.vram_total_mib);
  const vramMismatch=Number.isFinite(status?.vram_used_mib) && Number.isFinite(status?.vram_total_mib) && status.vram_total_mib>0 && status.vram_used_mib>status.vram_total_mib;
  return <section ref={live.ref} id="gpu-panel" className={embedded?"gpu-panel-content":"floating-panel"} aria-label="GPU 프로세스 정보">
    {!embedded && <h2>GPU 프로세스 정보</h2>}
    <div className="gpu-refresh"><LiveRefreshControl live={live} label="GPU 상태 자동 갱신"/><button ref={refreshRef} type="button" disabled={loading} onClick={()=>{restoreRefreshFocus.current=true;setRevision(value=>value+1);}}>{loading?"조회 중…":"새로고침"}</button></div>
    {checkedAt && <p className="gpu-checked">마지막 조회 성공 · <time dateTime={checkedAt.toISOString()}>{checkedAt.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false})}</time></p>}
    {error && <p role="alert">{error}{status && " · 아래는 마지막으로 조회한 정보입니다."}</p>}
    {!status && !error && <p>조회 중…</p>}
    {status && <>
      <p>{status.status==="idle" && !processes ? "GPU 상태 확인 불가" : ({busy:"GPU 사용 중",idle:"실행 중인 GPU 작업 없음"}[status.status] || "GPU 상태 확인 불가")}</p>
      {vramPercent && <div className="gpu-memory-meter"><span>VRAM 사용률 · {vramPercent}</span><meter aria-label="VRAM 사용률" min="0" max={status.vram_total_mib} value={status.vram_used_mib} aria-valuetext={vramPercent}/></div>}
      {vramMismatch && <p role="status">VRAM 사용량이 총량보다 커서 사용률을 계산할 수 없습니다. 다시 조회해 주세요.</p>}
      <details><summary>메모리{status.vram_total_mib != null && <> · VRAM {memory(status.vram_used_mib)} / {memory(status.vram_total_mib)}{vramPercent && ` · ${vramPercent}`}</>}</summary>
        {domains.length===0 && <p>측정된 메모리 정보 없음</p>}
        {domains.map(domain=><p key={domain}>{domain.toUpperCase()} · 사용 {memory(status[domain+"_used_mib"])} · 여유 {memory(status[domain+"_free_mib"])} · 총 {memory(status[domain+"_total_mib"])}</p>)}
      </details>
      <details><summary>프로세스 · {processes ? `${processes.length}개` : "확인 불가"}</summary>
        {!processes && <p>프로세스 목록을 제공받지 못했습니다. 다시 조회해 주세요.</p>}
        {processes?.length===0 && <p>조회된 프로세스 없음</p>}
        {processes?.map((process,index)=><details key={process.pid ?? process.id ?? index}>
          <summary>{process.command || "식별되지 않은 GPU 프로세스"} · PID {process.pid ?? "?"}</summary>
          {process.gpu_parent_pid && <p>부모 PID {process.gpu_parent_pid}</p>}
          <p>VRAM {memory(process.vram_memory_mib)} · GTT {memory(process.gtt_memory_mib)}</p>
          {process.id && <><p>프로세스 명령에서 추정한 작업 ID</p><JobIdentifier id={process.id} compact/>{processJobLink(process) && <p><a href={processJobLink(process)}>생성기 작업 진행 상세 보기</a></p>}</>}
        </details>)}
      </details>
    </>}
  </section>;
}
