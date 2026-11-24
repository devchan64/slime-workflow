import React,{useCallback,useEffect,useRef,useState} from "react";
import {observeLiveVisibility} from "./observeLiveVisibility.mjs";

export const LIVE_REFRESH_MS=30000;

export function useLiveRefresh(refresh,active=true){
  const [enabled,setEnabled]=useState(true),[element,setElement]=useState(null),[visible,setVisible]=useState(false);
  const callback=useRef(refresh);
  callback.current=refresh;
  const ref=useCallback(node=>setElement(node),[]);
  useEffect(()=>{
    setVisible(false);
    if(!element)return;
    return observeLiveVisibility(element,setVisible,{document,window,Observer:globalThis.IntersectionObserver});
  },[element]);
  useEffect(()=>{
    if(!enabled || !visible || !active)return;
    const timer=setInterval(()=>callback.current(),LIVE_REFRESH_MS);
    return ()=>clearInterval(timer);
  },[enabled,visible,active]);
  return {ref,enabled,setEnabled,visible,active};
}

export function LiveRefreshControl({live,label="자동 갱신",inactiveReason="일시 중지"}){
  return <label className="live-refresh"><input type="checkbox" checked={live.enabled} onChange={event=>live.setEnabled(event.target.checked)}/> {label} · 30초 간격{!live.active ? " · "+inactiveReason : live.enabled && !live.visible ? " · 화면에 보이면 갱신" : ""}</label>;
}
