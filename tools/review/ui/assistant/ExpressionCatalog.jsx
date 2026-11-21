import React, {useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

export default function ExpressionCatalog({query,choose}) {
  const [cursor,setCursor]=useState({});
  const [page,setPage]=useState(null);
  const [error,setError]=useState("");
  useEffect(()=>{
    let active=true;
    setPage(null);
    setError("");
    const timer=setTimeout(async ()=>{
      try {
        const result=await managementCommand("hermes-agent","hermes-expression-catalog",{query,limit:20,...cursor});
        if(active)setPage(result);
      } catch(problem) {
        if(active)setError(problem.message);
      }
    },200);
    return ()=>{active=false;clearTimeout(timer);};
  },[query,cursor]);
  return <section aria-label="표정 프리셋 검색">
    {error && <p role="alert">{error} <button onClick={()=>setCursor({})}>다시 조회</button></p>}
    {!error && !page && <p role="status">표정 조회 중…</p>}
    {page && <>
      <ResultTable table={{title:"등록 표정",summary:"전체 "+page.total+"개",columns:["표정","요청에 추가할 ID"],
        rows:page.records.map(row=>[row.label,<button onClick={()=>choose("표정 "+row.label,row.id)}>{row.id}</button>])}}/>
      {page.offset>0 && <button onClick={()=>setCursor({offset:Math.max(0,page.offset-20),snapshot:page.snapshot})}>이전 표정</button>}
      {page.next_offset!=null && <button onClick={()=>setCursor({offset:page.next_offset,snapshot:page.snapshot})}>다음 표정</button>}
    </>}
  </section>;
}
