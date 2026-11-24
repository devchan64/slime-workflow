import React,{useId,useState} from "react";
import {randomSeed} from "./randomSeed.mjs";

export default function SeedInput({value,onChange,max,required=true,error=""}) {
  const errorId=useId(),helpId=useId(),randomErrorId=useId();
  const [randomError,setRandomError]=useState("");
  const hasRange=Number.isSafeInteger(max) && max>=0;
  return <div className="seed-input"><label>시드<input type="number" min={0} max={max} step={1} required={required}
    aria-invalid={error ? true : undefined} aria-describedby={[hasRange || !required ? helpId : null,error ? errorId : null].filter(Boolean).join(" ") || undefined}
    value={value} onChange={event=>{setRandomError("");onChange(event.target.value);}}/></label>
    <button type="button" aria-describedby={randomError ? randomErrorId : undefined} onClick={()=>{let next;try{next=randomSeed(max);}catch{setRandomError("랜덤 시드를 만들 수 없습니다. 시드를 직접 입력하세요.");return;}setRandomError("");onChange(String(next));}}>랜덤 시드</button>
    {(hasRange || !required) && <small className="seed-input-help" id={helpId}>{hasRange ? `0부터 ${max.toLocaleString("ko-KR")}까지의 정수` : "정수"}{!required && " · 입력 선택 사항"}</small>}
    {error && <small id={errorId} className="seed-input-error">{error}</small>}
    {randomError && <p id={randomErrorId} className="seed-input-error" role="alert">{randomError}</p>}
  </div>;
}
