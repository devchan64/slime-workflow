import React,{useCallback,useEffect,useId,useRef,useState} from "react";
import {observeLiveVisibility} from "./observeLiveVisibility.mjs";

export const LIVE_REFRESH_MS=30000;

export function useLiveRefresh(refresh,active=true,interval=LIVE_REFRESH_MS){
  const [enabled,setEnabledState]=useState(true),[element,setElement]=useState(null),[visible,setVisible]=useState(false);
  const callback=useRef(refresh);
  const enabledRef=useRef(true),visibleRef=useRef(false),activeRef=useRef(active);
  callback.current=refresh;activeRef.current=active;
  const setEnabled=useCallback(value=>{const next=typeof value==='function' ? value(enabledRef.current) : value;enabledRef.current=next;setEnabledState(next);},[]);
  const ref=useCallback(node=>setElement(node),[]);
  useEffect(()=>{
    visibleRef.current=false;setVisible(false);
    if(!element)return;
    return observeLiveVisibility(element,value=>{visibleRef.current=value;setVisible(value);},{document,window,Observer:globalThis.IntersectionObserver});
  },[element]);
  useEffect(()=>{
    if(!enabled || !visible || !active)return;
    let running=true;
    const timer=setInterval(()=>{if(running && enabledRef.current && visibleRef.current && activeRef.current && document.visibilityState==='visible')callback.current();},interval);
    return ()=>{running=false;clearInterval(timer);};
  },[enabled,visible,active,interval]);
  return {ref,enabled,setEnabled,visible,active,interval};
}

export function LiveRefreshControl({live,label="자동 갱신",inactiveReason="일시 중지"}){
  const descriptionId=useId();
  return <label className="live-refresh"><input type="checkbox" aria-label={label} aria-describedby={descriptionId} checked={live.enabled} onChange={event=>live.setEnabled(event.target.checked)}/> {label} <span id={descriptionId}>· {(live.interval ?? LIVE_REFRESH_MS)/1000}초 간격{!live.active ? " · "+inactiveReason : live.enabled && !live.visible ? " · 화면에 보이면 갱신" : ""}</span></label>;
}
