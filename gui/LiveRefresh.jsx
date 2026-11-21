import React,{useCallback,useEffect,useRef,useState} from "react";

export const LIVE_REFRESH_MS=30000;

export function useLiveRefresh(refresh,active=true){
  const [enabled,setEnabled]=useState(true),[element,setElement]=useState(null),[visible,setVisible]=useState(false);
  const callback=useRef(refresh);
  callback.current=refresh;
  const ref=useCallback(node=>setElement(node),[]);
  useEffect(()=>{
    if(!element)return;
    let intersecting=false;
    const update=()=>setVisible(intersecting && document.visibilityState==="visible");
    const observer=new IntersectionObserver(entries=>{intersecting=entries[0]?.isIntersecting || false;update();});
    observer.observe(element);
    document.addEventListener("visibilitychange",update);
    return ()=>{observer.disconnect();document.removeEventListener("visibilitychange",update);};
  },[element]);
  useEffect(()=>{
    if(!enabled || !visible || !active)return;
    const timer=setInterval(()=>callback.current(),LIVE_REFRESH_MS);
    return ()=>clearInterval(timer);
  },[enabled,visible,active]);
  return {ref,enabled,setEnabled,visible,active};
}

export function LiveRefreshControl({live,label="자동 갱신"}){
  return <label className="live-refresh"><input type="checkbox" checked={live.enabled} onChange={event=>live.setEnabled(event.target.checked)}/> {label} · 30초 간격{!live.active && " · 일시 중지"}</label>;
}
