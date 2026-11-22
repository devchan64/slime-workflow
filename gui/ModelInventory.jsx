import React, {useEffect, useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return "확인 불가";
  const exact=bytes.toLocaleString("ko-KR")+"바이트";
  if (bytes < 1024) return exact;
  const units=["KiB","MiB","GiB","TiB"];
  const power=Math.min(Math.floor(Math.log(bytes)/Math.log(1024)),units.length);
  return (bytes/1024**power).toLocaleString("ko-KR",{maximumFractionDigits:2})+" "+units[power-1]+" ("+exact+")";
}

export function InventoryContents({inventory}) {
  return <><ResultTable table={{
    title: "저장된 모델 파일",
    summary: [
      "파일 " + inventory.count.toLocaleString() + "개",
      Number.isFinite(inventory.total_bytes) && formatBytes(inventory.total_bytes),
      inventory.incomplete && "일부 저장 위치 확인 실패",
      inventory.truncated && "앞의 " + inventory.files.length + "개 표시",
    ].filter(Boolean).join(" · "),
    columns: ["파일 경로", "크기"],
    rows: inventory.files.map(file => [file.path, formatBytes(file.bytes)]),
  }}/><p>파일 목록은 해시 검증 결과가 아닙니다.</p></>;
}

function InventoryFiles({service}) {
  const [revision, refresh] = useState(0);
  const [inventory, setInventory] = useState(null);
  const [error, setError] = useState("");
  const [checkedAt,setCheckedAt]=useState(null),[loading,setLoading]=useState(false);
  useEffect(() => {
    let active = true;
    let timer;
    async function read() {
      if(active)setLoading(true);
      try {
        const response = await managementCommand("model-downloads", "download-inventory");
        const model = response.models?.[service];
        if (!model || !Array.isArray(model.files) || !Number.isInteger(model.count)) {
          throw new Error("이 모델의 파일 목록을 확인할 수 없습니다.");
        }
        if (active) {
          setInventory(model);
          setCheckedAt(new Date());
          setError("");
        }
      } catch (problem) {
        if (active) setError(problem.message);
      } finally {
        if (active) {setLoading(false);timer = setTimeout(read, 30000);}
      }
    }
    read();
    return () => { active = false; clearTimeout(timer); };
  }, [service, revision]);
  return <>
    <button type="button" disabled={loading} onClick={() => refresh(value => value + 1)}>{loading ? "조회 중…" : "파일 목록 새로고침"}</button>
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {error && <p role="alert">{error}{inventory && " · 아래 목록은 마지막으로 확인한 정보입니다."}</p>}
    {inventory ? <InventoryContents inventory={inventory}/> : !error && <p role="status">파일 목록 확인 중…</p>}
  </>;
}

export default function ModelInventory({service}) {
  const [open, setOpen] = useState(false);
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>저장된 모델 파일 보기</summary>
    {open && <InventoryFiles key={service} service={service}/>}
  </details>;
}
