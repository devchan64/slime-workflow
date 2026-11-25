import React, {useEffect, useRef, useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";
import {validModelInventory} from "./modelInventoryValidation.mjs";
import {LiveRefreshControl,useLiveRefresh} from "./LiveRefresh.jsx";

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return "확인 불가";
  const exact=bytes.toLocaleString("ko-KR")+"바이트";
  if (bytes < 1024) return exact;
  const units=["KiB","MiB","GiB","TiB"];
  const power=Math.min(Math.floor(Math.log(bytes)/Math.log(1024)),units.length);
  return (bytes/1024**power).toLocaleString("ko-KR",{maximumFractionDigits:2})+" "+units[power-1]+" ("+exact+")";
}

export function InventoryContents({inventory}) {
  return <><div className="model-inventory-table"><ResultTable table={{
    title: "저장된 모델 파일",
    emptyMessage: inventory.incomplete ? "확인된 파일이 없습니다. 일부 저장 위치를 확인하지 못했습니다." : inventory.count>0 ? "표시할 파일이 없습니다. 목록을 다시 확인하세요." : "저장된 모델 파일이 없습니다.",
    summary: [
      "파일 " + inventory.count.toLocaleString() + "개",
      Number.isFinite(inventory.total_bytes) && formatBytes(inventory.total_bytes),
      inventory.incomplete && "일부 저장 위치 확인 실패",
      inventory.truncated && "앞의 " + inventory.files.length + "개 표시",
    ].filter(Boolean).join(" · "),
    columns: ["파일 경로", "크기"],
    rows: inventory.files.map(file => [file.path, formatBytes(file.bytes)]),
  }}/></div><p>파일 목록은 해시 검증 결과가 아닙니다.</p></>;
}

function InventoryFiles({service}) {
  const [revision, refresh] = useState(0);
  const [inventory, setInventory] = useState(null);
  const [error, setError] = useState("");
  const [checkedAt,setCheckedAt]=useState(null),[loading,setLoading]=useState(true);
  const pending=useRef(true);
  function requestRefresh(){if(pending.current)return;pending.current=true;setLoading(true);refresh(value=>value+1);}
  const live=useLiveRefresh(requestRefresh);
  useEffect(() => {
    let active = true;
    let controller;
    async function read() {
      if(!active)return;
      pending.current=true;setLoading(true);
      controller = new AbortController();
      let timedOut = false;
      const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 30000);
      try {
        const response = await untilAborted(managementCommand("model-downloads", "download-inventory", {}, {signal: controller.signal}),controller.signal);
        const model = response?.models?.[service];
        if (!validModelInventory(model)) {
          throw new Error("이 모델의 파일 목록을 확인할 수 없습니다.");
        }
        if (active) {
          setInventory(model);
          setCheckedAt(new Date());
          setError("");
        }
      } catch (problem) {
        if (active) setError(timedOut ? "파일 목록 조회 시간이 초과됐습니다. 다시 확인하세요." : typeof problem?.message==="string" && problem.message.trim() ? problem.message : "파일 목록을 조회할 수 없습니다.");
      } finally {
        clearTimeout(timeout);
        if (active) {pending.current=false;setLoading(false);}
      }
    }
    read();
    return () => { active = false; pending.current=false;controller?.abort(); };
  }, [service, revision]);
  return <div ref={live.ref}>
    <button type="button" aria-disabled={loading} onClick={requestRefresh}>{loading ? "조회 중…" : "파일 목록 새로고침"}</button>
    <LiveRefreshControl live={live} label="파일 목록 자동 갱신"/>
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {loading && <p role="status">{inventory ? "파일 목록을 다시 조회하고 있습니다. 아래는 마지막으로 확인한 목록입니다." : "파일 목록을 확인하고 있습니다."}</p>}
    {error && <p role="alert">{error}{inventory && " · 아래 목록은 마지막으로 확인한 정보입니다."}{loading && " · 다시 확인하고 있습니다."}</p>}
    {inventory && <InventoryContents inventory={inventory}/>}
  </div>;
}

export default function ModelInventory({service}) {
  const [open, setOpen] = useState(false);
  return <details className="model-inventory" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>저장된 모델 파일 보기</summary>
    {open && <InventoryFiles key={service} service={service}/>}
  </details>;
}
