import React from "react";

export default function QueuePagination({page,size,total,onPage,onSize,label}){
  const pages=Math.max(1,Math.ceil(total/size));
  const current=Math.min(page,pages-1);
  return <nav className="queue-pagination" aria-label={label}>
    <label>페이지 크기 <select value={size} onChange={event=>onSize(Number(event.target.value))}><option value={5}>5개</option><option value={10}>10개</option></select></label>
    <div><button type="button" disabled={current===0} onClick={()=>onPage(current-1)}>이전</button><span aria-live="polite"> {current+1} / {pages} 페이지 · {total}건 </span><button type="button" disabled={current>=pages-1} onClick={()=>onPage(current+1)}>다음</button></div>
  </nav>;
}
