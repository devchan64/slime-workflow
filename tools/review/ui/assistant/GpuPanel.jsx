import React, {useEffect, useState} from "react";

function memory(value) {
  return Number.isInteger(value) && value >= 0 ? value.toLocaleString() + " MiB" : "미측정";
}

export default function GpuPanel() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [copyNotice,setCopyNotice] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let timer;
    async function refresh() {
      try {
        const response = await fetch("/management/gpu-status", {cache:"no-store",signal:controller.signal});
        if (!response.ok) throw new Error("GPU 상태 조회 실패");
        const next = await response.json();
        if (!controller.signal.aborted) {setStatus(next);setError("");}
      } catch (problem) {
        if (!controller.signal.aborted) {setStatus(null);setError(problem.message);}
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(refresh,30000);
      }
    }
    refresh();
    return () => {controller.abort();clearTimeout(timer);};
  }, []);
  async function copy(id) {
    try {await navigator.clipboard.writeText(id);setCopyNotice("복사됨 · " + id);}
    catch {setCopyNotice("작업 ID를 선택해 복사하세요.");}
  }
  return <section id="gpu-panel" className="floating-panel" aria-label="GPU 프로세스 정보">
    <h2>GPU 프로세스 정보</h2>
    {error && <p role="alert">{error}</p>}
    {!status && !error && <p>조회 중…</p>}
    {status && <>
      <p>{{busy:"GPU 사용 중",idle:"실행 중인 GPU 작업 없음"}[status.status] || "GPU 상태 확인 불가"}</p>
      {["vram","gtt"].filter(domain=>status[domain+"_total_mib"] != null).map(domain=>
        <p key={domain}>{domain.toUpperCase()} · 사용 {memory(status[domain+"_used_mib"])} · 여유 {memory(status[domain+"_free_mib"])} · 총 {memory(status[domain+"_total_mib"])}</p>)}
      {(status.processes || []).map((process,index)=><section key={process.pid ?? index}>
        <strong>{process.command || "외부 GPU 작업"} · PID {process.pid ?? "?"}</strong>
        {process.gpu_parent_pid && <p>부모 PID {process.gpu_parent_pid}</p>}
        <p>VRAM {memory(process.vram_memory_mib)} · GTT {memory(process.gtt_memory_mib)}</p>
        {process.id && <p><code>{process.id}</code> <button onClick={()=>copy(process.id)}>작업 ID 복사</button></p>}
      </section>)}
      <p role="status">{copyNotice}</p>
    </>}
  </section>;
}
