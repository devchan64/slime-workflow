import React,{useState} from "react";

/** 접어도 본문을 유지하는 공용 생성기 섹션. 요약에는 조작 요소를 넣지 않는다. */
export default function GeneratorSectionCard({title,summary,children,defaultOpen=false,className="",cardRef,onOpenChange}){
  const [open,setOpen]=useState(defaultOpen);
  return <details ref={cardRef} className={`generator-section-card ${className}`} open={open} onToggle={event=>{const next=event.currentTarget.open;setOpen(next);onOpenChange?.(next);}}>
    <summary><span className="generator-section-card-heading" role="heading" aria-level="2">{title}</span>{summary && <span className="generator-section-card-summary">{summary}</span>}</summary>
    <div className="generator-section-card-body">{children}</div>
  </details>;
}
