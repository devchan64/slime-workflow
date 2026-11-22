import React, {useEffect, useRef, useState} from "react";
import {managementCommand} from "./managementCommand.js";

function restrictions(items) {
  return items.map(item => item.command+" · "+(item.reason ?? item.note)).join(" / ");
}

export default function ServiceRegistry({query}) {
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState(null);
  const [error, setError] = useState("");
  const [loading,setLoading]=useState(true),[receivedAt,setReceivedAt]=useState(null);
  const [revision, refresh] = useState(0);
  const listRef=useRef(null),focusNextPage=useRef(false);
  useEffect(()=>{if(page && focusNextPage.current){focusNextPage.current=false;listRef.current?.focus({preventScroll:true});listRef.current?.scrollIntoView({block:"start",inline:"nearest"});}},[page]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const timer = setTimeout(async () => {
      try {
        const result = await managementCommand("hermes-agent","hermes-service-registration",{query,offset,limit:10});
        if (!result || !Array.isArray(result.services) || !Number.isInteger(result.total) || result.services.some(row=>!row || typeof row.service!=="string" || ![row.commands,row.gateway_blocked,row.known_service_blocked,row.conditional_limitations,row.hermes_links].every(Array.isArray))) throw new Error("서비스 목록 형식을 확인할 수 없습니다.");
        if (active) {setPage(result);setReceivedAt(new Date());}
      } catch (problem) {
        if (active) {focusNextPage.current=false;setError(problem instanceof TypeError ? "서비스 목록에 연결하지 못했습니다. 다시 시도하세요." : problem.message);}
      } finally {if(active)setLoading(false);}
    }, 200);
    return () => {active = false; clearTimeout(timer);};
  }, [query,offset,revision]);
  return <section aria-label="서비스 등록 목록">
    <button disabled={loading} onClick={() => refresh(value => value+1)}>{loading?"조회 중…":"등록 목록 새로고침"}</button>
    {error && <p role="alert">{error}{page && " · 이전 조회 결과를 유지합니다."}</p>}
    {loading && page && <p role="status">새 목록을 조회 중입니다. 아래는 이전 결과입니다.</p>}
    {page ? <>
      <p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p>
      <h3 ref={listRef} tabIndex={-1}>등록 서비스</h3>
      <p>{query?.trim() ? <>검색어 · <strong>{query.trim()}</strong></> : "검색 조건 · 전체 서비스"}</p>
      <p>전체 {page.total}개 · {page.services.length}개 표시</p>
      {page.services.length===0 && <p role="status">{query?.trim() ? "검색 조건에 맞는 서비스가 없습니다. 검색어를 바꾸거나 지워 주세요." : "등록된 서비스가 없습니다."}</p>}
      <ul className="service-registry-list">{page.services.map(record=><li key={record.service}>
        <strong>{record.service}</strong>
        <details><summary>명령과 제한 확인</summary><dl>
          <dt>등록 명령</dt><dd>{record.commands.join(", ") || "기록 없음"}</dd>
          <dt>게이트웨이 명시 차단</dt><dd>{restrictions(record.gateway_blocked) || "기록 없음"}</dd>
          <dt>확인된 서비스 차단</dt><dd>{restrictions(record.known_service_blocked) || "기록 없음"}</dd>
          <dt>조건부 제한</dt><dd>{restrictions(record.conditional_limitations) || "기록 없음"}</dd>
          <dt>헤르메스 연결 기능</dt><dd>{record.hermes_links.join(", ") || "기록 없음"}</dd>
        </dl></details>
      </li>)}</ul>
      <p>{page.note}</p>
      {offset>0 && <button disabled={loading || !!error} onClick={() => {focusNextPage.current=true;setOffset(Math.max(0,offset-10));}}>이전 서비스</button>}
      {page.next_offset!=null && <button disabled={loading || !!error} onClick={() => {focusNextPage.current=true;setOffset(page.next_offset);}}>다음 서비스</button>}
    </> : !error && <p role="status">등록 서비스 조회 중…</p>}
  </section>;
}
