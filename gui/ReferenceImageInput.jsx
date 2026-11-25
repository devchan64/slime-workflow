import React, {useEffect,useId,useRef,useState} from "react";
import {referenceImageError,clipboardImageName,formatReferenceLimit} from "./referenceImageValidation.mjs";
import {imageRetryUrl} from "./imageRetryUrl.mjs";

async function withinTime(promise){
  let timer;
  try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error("이미지 확인 시간이 초과됐습니다. 다시 시도하세요.")),15000);})]);}
  finally{clearTimeout(timer);}
}

async function verifyImage(file,accept){
  if(accept==="image/png"){
    const signature=new Uint8Array(await withinTime(file.slice(0,8).arrayBuffer()));
    if(signature.join(",")!=="137,80,78,71,13,10,26,10")throw new Error("PNG 이미지 파일을 선택하세요.");
  }
  return new Promise((resolve,reject)=>{
    const url=URL.createObjectURL(file),image=new Image();let done=false;
    const timer=setTimeout(()=>finish(true),15000);
    const finish=error=>{if(done)return;done=true;clearTimeout(timer);image.onload=null;image.onerror=null;URL.revokeObjectURL(url);error ? reject(new Error("이미지 파일을 읽을 수 없습니다. 다른 파일을 선택하세요.")) : resolve();};
    image.onload=()=>finish(false);image.onerror=()=>finish(true);image.src=url;
  });
}

export default function ReferenceImageInput({label,source,onChange,onSelectionStart,onCheckingChange,accept="image/*",disabled=false,maxBytes=null,validate=null,describedBy}) {
  const input=useRef(null),pasteButton=useRef(null),removeButton=useRef(null),disabledRef=useRef(disabled),requestRef=useRef(0),restoreFocus=useRef(false),restorePasteFocus=useRef(false),restoreFileFocus=useRef(false);
  const previewRef=useRef(null),previewRetryRef=useRef(null),restorePreviewFocus=useRef(false),previewGeneration=useRef(0);
  const errorId=useId(),limitId=useId(),checkingId=useId();
  disabledRef.current=disabled;
  const [preview,setPreview]=useState(""),[error,setError]=useState(""),[checking,setChecking]=useState(false),[previewError,setPreviewError]=useState(false),[previewRevision,retryPreview]=useState(0);
  const checkingCallback=useRef(onCheckingChange);checkingCallback.current=onCheckingChange;
  function updateChecking(value){setChecking(value);checkingCallback.current?.(value);}
  useEffect(()=>()=>{requestRef.current+=1;checkingCallback.current?.(false);},[]);
  useEffect(()=>{if(disabled){requestRef.current+=1;restorePasteFocus.current=false;restoreFileFocus.current=false;updateChecking(false);}},[disabled]);
  useEffect(()=>{
    requestRef.current+=1;previewGeneration.current+=1;updateChecking(false);setError("");setPreviewError(false);retryPreview(0);
    if(restoreFocus.current){restoreFocus.current=false;const previous=removeButton.current;requestAnimationFrame(()=>{if((document.activeElement===document.body || document.activeElement===previous) && !disabledRef.current)input.current?.focus();});}
    if (!source) {setPreview("");return;}
    if (typeof source === "string") {setPreview(source);return;}
    const url=URL.createObjectURL(source);setPreview(url);
    return ()=>URL.revokeObjectURL(url);
  },[source]);
  useEffect(()=>{if(!checking && restorePasteFocus.current){restorePasteFocus.current=false;if(document.activeElement===document.body && !disabledRef.current)pasteButton.current?.focus();}},[checking]);
  useEffect(()=>{if(!checking && restoreFileFocus.current){restoreFileFocus.current=false;if(document.activeElement===document.body && !disabledRef.current)input.current?.focus();}},[checking]);
  useEffect(()=>{if(restorePreviewFocus.current){restorePreviewFocus.current=false;if(document.activeElement===document.body)(previewError ? previewRetryRef : previewRef).current?.focus();}},[previewError,previewRevision]);
  async function select(file){
    if(!file || disabledRef.current)return;
    onSelectionStart?.();
    const sequence=++requestRef.current;
    const problem=referenceImageError(file,accept,maxBytes);
    if(problem){updateChecking(false);setError(problem);return;}
    if(document.activeElement===input.current)restoreFileFocus.current=true;
    setError("");updateChecking(true);
    try {
      await verifyImage(file,accept);
      if(validate)await withinTime(validate(file));
      if(sequence===requestRef.current && !disabledRef.current)onChange(file);
    } catch(problem) {if(sequence===requestRef.current)setError(problem?.message || "이미지를 확인할 수 없습니다.");}
    finally {if(sequence===requestRef.current)updateChecking(false);}
  }
  async function paste(){
    if(disabledRef.current)return;
    restorePasteFocus.current=document.activeElement===pasteButton.current;
    onSelectionStart?.();
    const sequence=++requestRef.current;setError("");updateChecking(true);
    try {
      if(!navigator.clipboard?.read)throw new Error("클립보드 이미지 읽기를 지원하지 않습니다. 파일을 선택하거나 놓아 주세요.");
      const items=await withinTime(navigator.clipboard.read());
      for(const item of items){
        const type=accept==="image/png" ? item.types.find(value=>value==="image/png") : item.types.find(value=>value.startsWith("image/"));
        if(type){const blob=await withinTime(item.getType(type));if(sequence===requestRef.current){if(!disabledRef.current)select(new File([blob],clipboardImageName(type),{type}));else updateChecking(false);}return;}
      }
      throw new Error("클립보드에서 이미지를 찾을 수 없습니다.");
    } catch(problem){if(sequence===requestRef.current){updateChecking(false);setError(problem?.message || "클립보드를 읽을 수 없습니다. 파일을 선택하세요.");}}
  }
  return <div role="group" aria-label={label} className={"reference-image-input"+(disabled ? " is-disabled" : "")+(!source ? " is-empty" : "")} onClick={event=>{if(!source && !disabled && !checking && !event.target.closest('button, label, input, a'))input.current?.click();}} onDragOver={event=>event.preventDefault()} onDrop={event=>{event.preventDefault();select(event.dataTransfer.files[0]);}}>
    <span>{label}</span>
    {maxBytes!==null && <small id={limitId}>{accept==="image/png" ? "PNG · " : ""}파일당 최대 {formatReferenceLimit(maxBytes)}</small>}
    {preview ? previewError ? <div><p role="alert">{label} 미리보기를 불러오지 못했습니다. 첨부는 유지됩니다.</p><button ref={previewRetryRef} type="button" aria-label={label+" 미리보기 다시 불러오기"} onClick={()=>{restorePreviewFocus.current=document.activeElement===previewRetryRef.current;setPreviewError(false);retryPreview(value=>value+1);}}>미리보기 다시 불러오기</button></div> : <img ref={previewRef} tabIndex={-1} key={previewGeneration.current+":"+previewRevision} src={previewRevision ? imageRetryUrl(preview,previewRevision) : preview} alt={label+" 미리보기"} onError={event=>{if(event.currentTarget!==previewRef.current)return;restorePreviewFocus.current=document.activeElement===previewRef.current;setPreviewError(true);}}/> : !checking && <p>{disabled ? "현재 이미지를 선택할 수 없습니다." : "이미지를 여기에 놓거나 클릭해 파일을 선택하세요."}</p>}
    {preview && typeof source?.name==="string" && source.name && <small className="reference-image-name">선택한 파일 · {source.name}</small>}
    <div className="choice-buttons"><label className="reference-image-file">파일 선택<input ref={input} type="file" disabled={disabled || checking} accept={accept} aria-label={label} aria-invalid={Boolean(error)} aria-describedby={[describedBy,maxBytes!==null ? limitId : null,checking && checkingId,error ? errorId : null].filter(Boolean).join(" ") || undefined} onChange={event=>{select(event.target.files[0]);event.target.value="";}}/></label>
      <button ref={pasteButton} type="button" aria-label={label+" 클립보드 붙여넣기"} aria-describedby={[describedBy,checking && checkingId,error && errorId].filter(Boolean).join(" ") || undefined} disabled={disabled || checking} onClick={paste}>클립보드 붙여넣기</button>
      {preview && <button ref={removeButton} type="button" aria-label={label+" 이미지 제거"} aria-describedby={[describedBy,checking && checkingId].filter(Boolean).join(" ") || undefined} disabled={disabled || checking} onClick={()=>{restoreFocus.current=document.activeElement===removeButton.current;setError("");onChange(null);}}>이미지 제거</button>}</div>
    {checking && <p id={checkingId} role="status">{label} 확인 중…</p>}
    {error && <p id={errorId} role="alert">{error}{source && " 기존 이미지는 유지됩니다."}</p>}
  </div>;
}
