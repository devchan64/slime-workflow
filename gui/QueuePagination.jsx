import React, {useRef} from "react";

export default function QueuePagination({page,size,total,onPage,onSize,label,onPageFocus,sizes=[5,10]}){
  const pages=Math.max(1,Math.ceil(total/size));
  const current=Math.min(page,pages-1);
  const previous=useRef(null),next=useRef(null);
  function movePage(target,button,other){
    const focused=document.activeElement;
    onPage(target);
    requestAnimationFrame(()=>{if(document.activeElement!==document.body && document.activeElement!==focused)return;if(onPageFocus)onPageFocus();else if(button.current?.disabled)other.current?.focus();});
  }
  return <nav className="queue-pagination" aria-label={label}>
    <label>페이지 크기 <select value={size} onChange={event=>onSize(Number(event.target.value))}>{sizes.map(count=><option key={count} value={count}>{count}개</option>)}</select></label>
    <div><button ref={previous} type="button" disabled={current===0} onClick={()=>movePage(current-1,previous,next)}>이전</button><span aria-live="polite"> {current+1} / {pages} 페이지 · {total}건 </span><button ref={next} type="button" disabled={current>=pages-1} onClick={()=>movePage(current+1,next,previous)}>다음</button></div>
  </nav>;
}
