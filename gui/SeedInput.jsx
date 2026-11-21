import React from "react";
import {randomSeed} from "./randomSeed.mjs";

export default function SeedInput({value,onChange,max,required=true}) {
  return <div className="seed-input"><label>시드<input type="number" min={0} max={max} step={1} required={required}
    value={value} onChange={event=>onChange(event.target.value)}/></label>
    <button type="button" onClick={()=>onChange(String(randomSeed(max)))}>랜덤 시드</button>
  </div>;
}
