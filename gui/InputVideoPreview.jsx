import React,{useEffect,useRef,useState} from "react";

/** 사용자가 선택하거나 이력에서 복원한 파일을 브라우저에서만 재생한다. */
export default function InputVideoPreview({file,label}){
  const [preview,setPreview]=useState(null),[failedUrl,setFailedUrl]=useState(null);
  const videoRef=useRef(null);
  useEffect(()=>{
    setFailedUrl(null);
    if(!file){setPreview(null);return;}
    const url=URL.createObjectURL(file);
    setPreview({file,url});
    return ()=>URL.revokeObjectURL(url);
  },[file]);
  if(!file || !preview || preview.file!==file)return null;
  return <div className="input-video-preview"><p>{label} 미리보기</p><video ref={videoRef} key={preview.url} aria-label={label+" 미리보기"} controls playsInline preload="metadata" src={preview.url} onError={event=>{if(event.currentTarget===videoRef.current)setFailedUrl(preview.url);}}/>{failedUrl===preview.url && <p role="alert">{label} 영상을 브라우저에서 재생할 수 없습니다. 다른 재생기에서 파일을 확인하세요.</p>}</div>;
}
