import React,{useState} from "react";

export default function AnimateInputs() {
  const [prompt,setPrompt]=useState("");
  const [seed,setSeed]=useState("42");
  const words=prompt.trim()?prompt.trim().split(/\s+/).length:0;
  return (
    <fieldset><legend>캐릭터 동작 전사 입력</legend>
      <label>캐릭터 참조 PNG · 832×480<input type="file" accept="image/png"/></label>
      <label>RGB 동작 MP4 · 16fps 샘플링<input type="file" accept="video/mp4"/></label>
      <label>캐릭터 외형·배경 설명<textarea maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <p>원문 {words}단어 · 최종 {words}단어 · 원문 그대로 전달</p>
      <label>프레임<input type="number" min={5} max={81} step={4} defaultValue={21}/></label>
      <label>스텝<input type="number" min={2} max={50} defaultValue={40}/></label>
      <label>시드<input type="number" min={0} max={2147483647} value={seed} onChange={event=>setSeed(event.target.value)}/></label>
      <button type="button" onClick={()=>setSeed(String(crypto.getRandomValues(new Uint32Array(1))[0] >>> 1))}>랜덤 시드</button>
      <p>공식 Base BF16 · 공식 스케줄러 및 CFG · AMD ROCm GPU 연산</p>
    </fieldset>
  );
}
