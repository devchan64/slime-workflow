import React,{useState} from "react";

export default function AnimateInputs({saved}) {
  const [prompt,setPrompt]=useState(saved?.request.prompt ?? "");
  const [seed,setSeed]=useState(saved?.request.seed ?? "42");
  const words=prompt.trim()?prompt.trim().split(/\s+/).length:0;
  return (
    <fieldset><legend>캐릭터 동작 전사 입력</legend>
      {saved && <section><p>복원한 작업 {saved.id}</p><img alt="저장된 참조 이미지" src={saved.reference} style={{maxWidth:"100%"}}/><video aria-label="저장된 동작 영상" controls preload="metadata" src={saved.motion}/></section>}
      <label>캐릭터 참조 PNG · 832×480<input type="file" accept="image/png"/></label>
      <label>RGB 동작 MP4 · 16fps 샘플링<input type="file" accept="video/mp4"/></label>
      <label>캐릭터 외형·배경 설명<textarea maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <p>원문 {words}단어 · 최종 {words}단어 · 원문 그대로 전달</p>
      <label>프레임<input type="number" min={5} max={81} step={4} defaultValue={saved?.request.frames ?? 21}/></label>
      <label>스텝<input type="number" min={2} max={50} defaultValue={saved?.request.steps ?? 40}/></label>
      <label>시드<input type="number" min={0} max={2147483647} value={seed} onChange={event=>setSeed(event.target.value)}/></label>
      <button type="button" onClick={()=>setSeed(String(crypto.getRandomValues(new Uint32Array(1))[0] >>> 1))}>랜덤 시드</button>
      <p>공식 Base BF16 · 공식 스케줄러 및 CFG · AMD ROCm GPU 연산</p>
    </fieldset>
  );
}
