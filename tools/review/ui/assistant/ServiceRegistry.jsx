import React, {useEffect, useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

function restrictions(items) {
  return items.map(item => item.command+" · "+(item.reason ?? item.note)).join(" / ");
}

export default function ServiceRegistry({query}) {
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState(null);
  const [error, setError] = useState("");
  const [revision, refresh] = useState(0);
  useEffect(() => {
    let active = true;
    setPage(null);
    setError("");
    const timer = setTimeout(async () => {
      try {
        const result = await managementCommand("hermes-agent","hermes-service-registration",{query,offset,limit:10});
        if (active) setPage(result);
      } catch (problem) {
        if (active) setError(problem.message);
      }
    }, 200);
    return () => {active = false; clearTimeout(timer);};
  }, [query,offset,revision]);
  return <section aria-label="서비스 등록 목록">
    <button onClick={() => refresh(value => value+1)}>등록 목록 새로고침</button>
    {error && <p role="alert">{error}</p>}
    {page ? <>
      <ResultTable table={{
        title:"등록 서비스", summary:"전체 "+page.total+"개 · "+page.services.length+"개 표시",
        columns:["서비스","등록 정보"],
        rows:page.services.map(record => [record.service,
          <details><summary>명령과 제한 확인</summary><dl>
            <dt>등록 명령</dt><dd>{record.commands.join(", ")}</dd>
            <dt>게이트웨이 명시 차단</dt><dd>{restrictions(record.gateway_blocked) || "기록 없음"}</dd>
            <dt>확인된 서비스 차단</dt><dd>{restrictions(record.known_service_blocked) || "기록 없음"}</dd>
            <dt>조건부 제한</dt><dd>{restrictions(record.conditional_limitations) || "기록 없음"}</dd>
            <dt>헤르메스 연결 기능</dt><dd>{record.hermes_links.join(", ") || "기록 없음"}</dd>
          </dl></details>,
        ]),
      }}/>
      <p>{page.note}</p>
      {offset>0 && <button onClick={() => setOffset(Math.max(0,offset-10))}>이전 서비스</button>}
      {page.next_offset!=null && <button onClick={() => setOffset(page.next_offset)}>다음 서비스</button>}
    </> : !error && <p role="status">등록 서비스 조회 중…</p>}
  </section>;
}
