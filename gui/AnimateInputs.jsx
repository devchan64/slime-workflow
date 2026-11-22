import PromptWordCount from "./PromptWordCount.jsx";
import SeedInput from "./SeedInput.jsx";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import React,{useEffect,useRef,useState} from "react";

export default function AnimateInputs({saved}) {
  const [prompt,setPrompt]=useState(saved?.request.prompt ?? "");
  const [seed,setSeed]=useState(saved?.request.seed ?? "42");
  const [reference,setReference]=useState(saved?.reference ?? null);
  const [motionError,setMotionError]=useState(false);
  const [motionFile,setMotionFile]=useState(null);
  const motionInput=useRef(null);
  const [frames,setFrames]=useState(saved?.request.frames ?? 21);
  const [steps,setSteps]=useState(saved?.request.steps ?? 40);
  useEffect(()=>{setPrompt(saved?.request.prompt ?? "");setSeed(saved?.request.seed ?? "42");setReference(saved?.reference ?? null);setFrames(saved?.request.frames ?? 21);setSteps(saved?.request.steps ?? 40);setMotionError(false);setMotionFile(null);if(motionInput.current)motionInput.current.value="";},[saved]);
  return (
    <fieldset className="animate-inputs"><legend>캐릭터 동작 전사 입력</legend>
      {saved && <section><p>복원한 작업</p><JobIdentifier id={saved.id} compact/><video key={saved.motion} aria-label="저장된 동작 영상" controls preload="metadata" src={saved.motion} onError={()=>setMotionError(true)}/>
        {motionError && <p role="status">이 브라우저에서 저장된 동작 영상을 재생할 수 없습니다. 원본 파일을 열어 확인하세요.</p>}
        <a href={saved.motion} target="_blank" rel="noreferrer">동작 영상 원본 열기</a></section>}
      <ReferenceImageInput label="캐릭터 참조 PNG · 832×480" source={reference} onChange={setReference} accept="image/png"/>
      <div className="animate-motion-file"><span>RGB 동작 MP4 · 16fps 샘플링</span><label className="reference-image-file">영상 파일 선택<input ref={motionInput} aria-label="RGB 동작 MP4 · 16fps 샘플링" type="file" accept="video/mp4" onChange={event=>setMotionFile(event.target.files[0] || null)}/></label>{motionFile && <small>선택한 파일 · {motionFile.name}</small>}</div>
      <label>캐릭터 외형·배경 설명<textarea maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <p><PromptWordCount text={prompt} final/> · 원문 그대로 전달</p>
      <label>프레임<input type="number" min={5} max={81} step={4} value={frames} onChange={event=>setFrames(event.target.value)}/></label>
      <label>스텝<input type="number" min={2} max={50} value={steps} onChange={event=>setSteps(event.target.value)}/></label>
      <SeedInput value={seed} max={2147483647} onChange={setSeed} required={false}/>
      <p>공식 Base BF16 · 공식 스케줄러 및 CFG · AMD ROCm GPU 연산</p>
    </fieldset>
  );
}
