import React, {useEffect,useRef,useState} from "react";
import {referenceImageError} from "./referenceImageValidation.mjs";

async function verifyImage(file,accept){
  if(accept==="image/png"){
    const signature=new Uint8Array(await file.slice(0,8).arrayBuffer());
    if(signature.join(",")!=="137,80,78,71,13,10,26,10")throw new Error("PNG 이미지 파일을 선택하세요.");
  }
  return new Promise((resolve,reject)=>{
    const url=URL.createObjectURL(file),image=new Image();
    const finish=error=>{URL.revokeObjectURL(url);error ? reject(new Error("이미지 파일을 읽을 수 없습니다. 다른 파일을 선택하세요.")) : resolve();};
    image.onload=()=>finish(false);image.onerror=()=>finish(true);image.src=url;
  });
}

export default function ReferenceImageInput({label,source,onChange,onSelectionStart,accept="image/*",disabled=false,maxBytes=null,validate=null,describedBy}) {
  const input=useRef(null),disabledRef=useRef(disabled),requestRef=useRef(0),restoreFocus=useRef(false);
  disabledRef.current=disabled;
  const [preview,setPreview]=useState(""),[error,setError]=useState(""),[checking,setChecking]=useState(false);
  useEffect(()=>()=>{requestRef.current+=1;},[]);
  useEffect(()=>{
    requestRef.current+=1;setChecking(false);setError("");
    if(source && restoreFocus.current)restoreFocus.current=false;
    if (!source) {setPreview("");return;}
    if (typeof source === "string") {setPreview(source);return;}
    const url=URL.createObjectURL(source);setPreview(url);
    return ()=>URL.revokeObjectURL(url);
  },[source]);
  useEffect(()=>{
    if(preview || !restoreFocus.current)return;
    restoreFocus.current=false;
    if(document.activeElement===document.body && !disabledRef.current)input.current?.focus();
  },[preview]);
  async function select(file){
    if(!file || disabledRef.current)return;
    onSelectionStart?.();
    const sequence=++requestRef.current;
    const problem=referenceImageError(file,accept,maxBytes);
    if(problem){setChecking(false);setError(problem);return;}
    setError("");setChecking(true);
    try {
      await verifyImage(file,accept);
      if(validate)await validate(file);
      if(sequence===requestRef.current && !disabledRef.current)onChange(file);
    } catch(problem) {if(sequence===requestRef.current)setError(problem.message || "이미지를 확인할 수 없습니다.");}
    finally {if(sequence===requestRef.current)setChecking(false);}
  }
  async function paste(){
    if(disabledRef.current)return;
    onSelectionStart?.();
    const sequence=++requestRef.current;setError("");setChecking(true);
    try {
      if(!navigator.clipboard?.read)throw new Error("클립보드 이미지 읽기를 지원하지 않습니다. 파일을 선택하거나 놓아 주세요.");
      const items=await navigator.clipboard.read();
      for(const item of items){
        const type=accept==="image/png" ? item.types.find(value=>value==="image/png") : item.types.find(value=>value.startsWith("image/"));
        if(type){const blob=await item.getType(type);if(sequence===requestRef.current){if(!disabledRef.current)select(new File([blob],"clipboard.png",{type}));else setChecking(false);}return;}
      }
      throw new Error("클립보드에서 이미지를 찾을 수 없습니다.");
    } catch(problem){if(sequence===requestRef.current){setChecking(false);setError(problem.message || "클립보드를 읽을 수 없습니다. 파일을 선택하세요.");}}
  }
  return <div className={"reference-image-input"+(disabled ? " is-disabled" : "")} onDragOver={event=>event.preventDefault()} onDrop={event=>{event.preventDefault();select(event.dataTransfer.files[0]);}}>
    <span>{label}</span>
    {maxBytes!==null && <small>PNG · 파일당 최대 {maxBytes/1000000}MB</small>}
    {preview ? <img src={preview} alt={label+" 미리보기"}/> : <p>{disabled ? "현재 이미지를 선택할 수 없습니다." : "이미지를 여기에 놓거나 파일을 선택하세요."}</p>}
    {preview && typeof source?.name==="string" && source.name && <small className="reference-image-name">선택한 파일 · {source.name}</small>}
    <div className="choice-buttons"><label className="reference-image-file">파일 선택<input ref={input} type="file" disabled={disabled || checking} accept={accept} aria-label={label} aria-describedby={describedBy} onChange={event=>{select(event.target.files[0]);event.target.value="";}}/></label>
      <button type="button" disabled={disabled || checking} onClick={paste}>클립보드 붙여넣기</button>
      {preview && <button type="button" disabled={disabled || checking} onClick={()=>{restoreFocus.current=true;setError("");onChange(null);}}>이미지 제거</button>}</div>
    {checking && <p role="status">이미지 확인 중…</p>}
    {error && <p role="alert">{error}{source && " 기존 이미지는 유지됩니다."}</p>}
  </div>;
}
