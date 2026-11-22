import React,{useEffect,useState} from "react";

/** 사용자가 선택하거나 이력에서 복원한 파일을 브라우저에서만 재생한다. */
export default function InputVideoPreview({file,label}){
  const [preview,setPreview]=useState(null),[failed,setFailed]=useState(false);
  useEffect(()=>{
    setFailed(false);
    if(!file){setPreview(null);return;}
    const url=URL.createObjectURL(file);
    setPreview({file,url});
    return ()=>URL.revokeObjectURL(url);
  },[file]);
  if(!file || !preview || preview.file!==file)return null;
  return <div className="input-video-preview"><p>{label} 미리보기</p><video key={preview.url} aria-label={label+" 미리보기"} controls playsInline preload="metadata" src={preview.url} onError={()=>setFailed(true)}/>{failed && <p role="alert">브라우저에서 이 영상을 재생할 수 없습니다. 다른 재생기에서 파일을 확인하세요.</p>}</div>;
}
