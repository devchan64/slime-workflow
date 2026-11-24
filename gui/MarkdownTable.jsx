import React,{useEffect,useId,useRef,useState} from "react";
import {observeTableOverflow,scrollTableOnArrow} from "./observeTableOverflow.mjs";

export default function MarkdownTable({node,children,...props}) {
  const scrollRef=useRef(null),tableRef=useRef(null),[overflow,setOverflow]=useState(false);
  const scrollHelpId=useId();
  useEffect(()=>{
    if(!scrollRef.current)return;
    return observeTableOverflow(scrollRef.current,tableRef.current,setOverflow,{window,Observer:globalThis.ResizeObserver});
  },[children]);
  return <>{overflow && <p id={scrollHelpId}>표에 초점을 두고 좌우 방향키로 스크롤할 수 있습니다.</p>}<div ref={scrollRef} className="result-table-scroll" role={overflow ? "region" : undefined} aria-label={overflow ? "본문 표 가로 스크롤" : undefined} aria-describedby={overflow ? scrollHelpId : undefined} tabIndex={overflow ? 0 : undefined} onKeyDown={scrollTableOnArrow}><table ref={tableRef} {...props}>{children}</table></div></>;
}
