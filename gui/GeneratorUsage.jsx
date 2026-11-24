import React,{useEffect,useRef,useState} from "react";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import MarkdownTable from "./MarkdownTable.jsx";
import {readGeneratorUsage} from "./readGeneratorUsage.mjs";

export default function GeneratorUsage({generator}) {
  const [open,setOpen]=useState(false),[content,setContent]=useState(null),[error,setError]=useState(""),[revision,setRevision]=useState(0);
  const retryRef=useRef(null),contentRef=useRef(null),restoreFocus=useRef(false),retrying=useRef(false);
  useEffect(()=>{restoreFocus.current=false;},[open,generator]);
  const visibleContent=content?.generator===generator ? content.text : null;
  const visibleError=error?.generator===generator ? error.message : "";
  useEffect(()=>{if(restoreFocus.current && (visibleError || visibleContent!==null)){restoreFocus.current=false;if(document.activeElement===document.body)(visibleError ? retryRef : contentRef).current?.focus();}},[visibleError,visibleContent]);
  useEffect(()=>{
    if(!open)return;
    const controller=new AbortController();let active=true,timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setContent(null);setError("");
    (async()=>{try{
      const text=await readGeneratorUsage(generator,controller.signal);
      if(active && !controller.signal.aborted)setContent({generator,text});
    }catch(problem){if(active && (problem.name!=="AbortError" || timedOut))setError({generator,message:timedOut ? "사용설명 조회 시간이 초과됐습니다. 다시 확인하세요." : problem.message || "사용설명을 읽을 수 없습니다."});}finally{clearTimeout(timer);if(active)retrying.current=false;}})();
    return ()=>{active=false;retrying.current=false;clearTimeout(timer);controller.abort();};
  },[open,generator,revision]);
  return <GeneratorSectionCard title="사용설명" summary="사용 방법과 제한 사항" onOpenChange={setOpen}>
    {open && <>{visibleError ? <><p role="alert">{visibleError}</p><button ref={retryRef} type="button" onClick={()=>{if(retrying.current)return;retrying.current=true;restoreFocus.current=document.activeElement===retryRef.current;setRevision(x=>x+1);}}>다시 불러오기</button></> : visibleContent===null ? <p role="status">사용설명을 불러오는 중…</p> : visibleContent.trim() ? <div ref={contentRef} tabIndex={-1} aria-label="사용설명 본문" className="assistant-markdown" style={{overflowWrap:"anywhere"}}><Markdown remarkPlugins={[remarkGfm]} components={{table:MarkdownTable}} skipHtml>{visibleContent}</Markdown></div> : <p ref={contentRef} tabIndex={-1}>등록된 사용설명 내용이 없습니다.</p>}</>}
  </GeneratorSectionCard>;
}
