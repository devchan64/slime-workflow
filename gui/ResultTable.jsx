import React, {useEffect,useId,useRef,useState} from "react";
import {observeTableOverflow,scrollTableOnArrow} from "./observeTableOverflow.mjs";

export default function ResultTable({table}) {
  const scrollRef=useRef(null),tableRef=useRef(null),[overflow,setOverflow]=useState(false);
  const scrollHelpId=useId();
  useEffect(()=>{
    const node=scrollRef.current;
    if(!node)return;
    return observeTableOverflow(node,tableRef.current,setOverflow,{window,Observer:globalThis.ResizeObserver});
  },[table]);
  return <section className="result-table"><strong>{table.title}</strong>{table.summary!=null && table.summary!=="" && <p>{table.summary}</p>}
    {overflow && <p id={scrollHelpId}>표에 초점을 두고 좌우 방향키로 스크롤할 수 있습니다.</p>}
    <div ref={scrollRef} className="result-table-scroll" role={overflow ? "region" : undefined} aria-label={overflow ? table.title+" 표 가로 스크롤" : undefined} aria-describedby={overflow ? scrollHelpId : undefined} tabIndex={overflow ? 0 : undefined} onKeyDown={scrollTableOnArrow}>
    <table ref={tableRef} aria-label={table.title}><thead><tr>
      {table.columns.map(column=><th key={column} scope="col">{column}</th>)}
    </tr></thead><tbody>
      {table.rows.map((row,index)=><tr key={table.rowKeys?.[index] ?? index}>{row.map((value,i)=><td key={i}>{value}</td>)}</tr>)}
      {table.rows.length===0 && <tr><td colSpan={table.columns.length}>조회된 항목이 없습니다.</td></tr>}
    </tbody></table></div>
  </section>;
}
