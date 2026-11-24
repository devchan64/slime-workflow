import React,{useEffect,useRef,useState} from "react";
import {startImageLoadDeadline} from "./imageLoadDeadline.mjs";
import {imageRetryUrl} from "./imageRetryUrl.mjs";

export default function RecoverableImage(props) {
  return <RecoverableImageForSource key={props.src} {...props}/>;
}

function RecoverableImageForSource({src,name,maxHeight=420,kind="원본"}) {
  const [failed,setFailed]=useState(false),[loaded,setLoaded]=useState(false),[revision,retry]=useState(0);
  const image=useRef(null),button=useRef(null),restoreFocus=useRef(false),cancelDeadline=useRef(null);
  useEffect(()=>{
    if(!restoreFocus.current)return;
    restoreFocus.current=false;
    if(document.activeElement===document.body)(failed ? button : image).current?.focus();
  },[failed,revision]);
  useEffect(()=>{
    if(loaded || failed)return;
    const cancel=startImageLoadDeadline(()=>{restoreFocus.current=document.activeElement===image.current;setFailed(true);});
    cancelDeadline.current=cancel;
    return ()=>{cancel();if(cancelDeadline.current===cancel)cancelDeadline.current=null;};
  },[loaded,failed,revision,src]);
  return failed ? <div><p role="alert">{name} {kind} 이미지를 불러오지 못했습니다.</p><button ref={button} type="button" aria-label={`${name} ${kind} 이미지 다시 불러오기`} onClick={()=>{restoreFocus.current=document.activeElement===button.current;setLoaded(false);setFailed(false);retry(value=>value+1);}}>이미지 다시 불러오기</button></div> : <>
    {!loaded && <p role="status">{name} {kind} 이미지를 불러오는 중입니다.</p>}
    <img className="recoverable-image" key={revision} ref={image} tabIndex={-1} src={imageRetryUrl(src,revision)} alt={name+" "+kind} style={{maxWidth:"100%",maxHeight,objectFit:"contain"}} onLoad={event=>{if(event.currentTarget!==image.current)return;cancelDeadline.current?.();setLoaded(true);}} onError={event=>{if(event.currentTarget!==image.current)return;cancelDeadline.current?.();restoreFocus.current=document.activeElement===image.current;setFailed(true);}}/></>;
}
