import React, {useEffect, useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

function InventoryFiles({service}) {
  const [revision, refresh] = useState(0);
  const [inventory, setInventory] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    let timer;
    async function read() {
      try {
        const response = await managementCommand("model-downloads", "download-inventory");
        const model = response.models?.[service];
        if (!model || !Array.isArray(model.files) || !Number.isInteger(model.count)) {
          throw new Error("이 모델의 파일 목록을 확인할 수 없습니다.");
        }
        if (active) {
          setInventory(model);
          setError("");
        }
      } catch (problem) {
        if (active) setError(problem.message);
      } finally {
        if (active) timer = setTimeout(read, 30000);
      }
    }
    read();
    return () => { active = false; clearTimeout(timer); };
  }, [service, revision]);
  return <>
    <button type="button" onClick={() => refresh(value => value + 1)}>파일 목록 새로고침</button>
    {error && <p role="alert">{error}</p>}
    {inventory ? <ResultTable table={{
      title: "저장된 모델 파일",
      summary: [
        "파일 " + inventory.count.toLocaleString() + "개",
        Number.isFinite(inventory.total_bytes) && inventory.total_bytes.toLocaleString() + "바이트",
        inventory.incomplete && "일부 저장 위치 확인 실패",
        inventory.truncated && "앞의 " + inventory.files.length + "개 표시",
      ].filter(Boolean).join(" · "),
      columns: ["파일 경로", "크기 (바이트)"],
      rows: inventory.files.map(file => [file.path, file.bytes.toLocaleString()]),
    }}/> : !error && <p role="status">파일 목록 확인 중…</p>}
  </>;
}

export default function ModelInventory({service}) {
  const [open, setOpen] = useState(false);
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>저장된 모델 파일 보기</summary>
    {open && <InventoryFiles key={service} service={service}/>}
  </details>;
}
