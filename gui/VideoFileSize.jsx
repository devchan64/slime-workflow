import React,{useEffect,useState} from "react";

export default function VideoFileSize({url,inline=false}){
  const [state,setState]=useState({url,size:null,loading:true});
  useEffect(()=>{
    const controller=new AbortController(); let active=true;
    const timer=setTimeout(()=>controller.abort(),15000);
    setState({url,size:null,loading:true});
    (async()=>{try{
      const response=await fetch(url,{headers:{Range:"bytes=0-0"},cache:"no-store",signal:controller.signal});
      const match=response.status===206 && /^bytes 0-0\/(\d+)$/.exec(response.headers.get("Content-Range") || "");
      const size=match ? Number(match[1]) : NaN;
      if(response.body) await response.body.cancel();
      if(active)setState({url,size:Number.isSafeInteger(size) && size>0 ? size : null,loading:false});
    }catch{if(active)setState({url,size:null,loading:false});}finally{clearTimeout(timer);}})();
    return ()=>{active=false;clearTimeout(timer);controller.abort();};
  },[url]);
  const text=state.url!==url || state.loading ? "결과 영상 용량 확인 중…" : "결과 영상 용량 · "+(state.size===null ? "확인할 수 없음" : state.size<1024 ? state.size+" B" : state.size<1048576 ? (state.size/1024).toFixed(1)+" KiB" : (state.size/1048576).toFixed(2)+" MiB");
  return inline ? <span className="history-card-summary">{text}</span> : <p>{text}</p>;
}

