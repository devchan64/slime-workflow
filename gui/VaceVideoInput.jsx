import React,{useId} from "react";
import InputVideoPreview from "./InputVideoPreview.jsx";

export default function VaceVideoInput({label,visible,file,checking,info,error,historyRevision,onSelect}) {
  const helpId=useId(),errorId=useId();
  return <div><label>{label}<input key={historyRevision} type="file" accept="video/mp4" required={visible && !file} disabled={!visible}
    aria-invalid={error ? true : undefined} aria-describedby={[helpId,error ? errorId : null].filter(Boolean).join(" ")}
    onChange={event=>{onSelect(event.target.files[0]);event.target.value="";}}/></label>
    <p id={helpId}>MP4 · 파일당 최대 32MiB{file && " · 선택: "+file.name}</p>
    {checking && <p role="status">영상 정보 확인 중…</p>}
    {info && <p>{info.summary}</p>}
    {error && <p id={errorId} role="alert">{error}{file && " 기존 영상은 유지됩니다."}</p>}
    {visible && <InputVideoPreview file={file} label={label}/>}</div>;
}
