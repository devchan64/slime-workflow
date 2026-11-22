import React,{useId} from "react";
import {randomSeed} from "./randomSeed.mjs";

export default function SeedInput({value,onChange,max,required=true,error=""}) {
  const errorId=useId();
  return <div className="seed-input"><label>시드<input type="number" min={0} max={max} step={1} required={required}
    aria-invalid={error ? true : undefined} aria-describedby={error ? errorId : undefined}
    value={value} onChange={event=>onChange(event.target.value)}/></label>
    <button type="button" onClick={()=>onChange(String(randomSeed(max)))}>랜덤 시드</button>
    {error && <small id={errorId} className="seed-input-error">{error}</small>}
  </div>;
}
