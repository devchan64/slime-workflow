import React,{useEffect,useState} from "react";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function GeneratorUsage({generator}) {
  const [open,setOpen]=useState(false),[content,setContent]=useState(null),[error,setError]=useState(""),[revision,setRevision]=useState(0);
  useEffect(()=>{
    if(!open)return;
    const controller=new AbortController();let active=true;
    setContent(null);setError("");
    (async()=>{try{
      const response=await fetch("/management/assistant/usage/"+encodeURIComponent(generator),{cache:"no-store",signal:controller.signal});
      if(!response.ok)throw new Error("사용설명 조회 실패 · HTTP "+response.status);
      const result=await response.json();
      if(typeof result.content!=="string")throw new Error("사용설명 응답을 확인할 수 없습니다.");
      if(active)setContent(result.content);
    }catch(problem){if(active && problem.name!=="AbortError")setError(problem.message || "사용설명을 읽을 수 없습니다.");}})();
    return ()=>{active=false;controller.abort();};
  },[open,generator,revision]);
  return <GeneratorSectionCard title="사용설명" summary="사용 방법과 제한 사항" onOpenChange={setOpen}>
    {open && <>{error ? <><p role="alert">{error}</p><button type="button" onClick={()=>setRevision(x=>x+1)}>다시 불러오기</button></> : content===null ? <p role="status">사용설명을 불러오는 중…</p> : <div className="assistant-markdown" style={{overflowWrap:"anywhere"}}><Markdown remarkPlugins={[remarkGfm]} skipHtml>{content}</Markdown></div>}</>}
  </GeneratorSectionCard>;
}
