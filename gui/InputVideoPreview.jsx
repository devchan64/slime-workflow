import React,{useEffect,useRef,useState} from "react";

/** 사용자가 선택하거나 이력에서 복원한 파일을 브라우저에서만 재생한다. */
export default function InputVideoPreview({file,label}){
  const [preview,setPreview]=useState(null),[failedUrl,setFailedUrl]=useState(null),[failedFile,setFailedFile]=useState(null);
  const videoRef=useRef(null);
  useEffect(()=>{
    setFailedUrl(null);setFailedFile(null);
    if(!file){setPreview(null);return;}
    let url;
    try{url=URL.createObjectURL(file);}catch{setPreview(null);setFailedFile(file);return;}
    setPreview({file,url});
    return ()=>URL.revokeObjectURL(url);
  },[file]);
  if(!file)return null;
  if(failedFile===file)return <p role="alert">{label} 미리보기를 준비할 수 없습니다. 파일을 다시 선택하거나 다른 재생기에서 확인하세요.</p>;
  if(!preview || preview.file!==file)return null;
  return <div className="input-video-preview"><p>{label} 미리보기</p><video ref={videoRef} key={preview.url} aria-label={label+" 미리보기"} controls playsInline preload="metadata" src={preview.url} onError={event=>{if(event.currentTarget===videoRef.current)setFailedUrl(preview.url);}}/>{failedUrl===preview.url && <p role="alert">{label} 파일을 브라우저에서 재생할 수 없습니다. 다른 재생기에서 파일을 확인하세요.</p>}</div>;
}
