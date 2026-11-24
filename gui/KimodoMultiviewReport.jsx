import React,{useEffect,useId,useRef,useState} from "react";
import readReference from "./readReference.js";
import KimodoJointWeights from "./KimodoJointWeights.jsx";
import ResultTable from "./ResultTable.jsx";
import {untilAborted} from "./managementCommand.js";

function BundleDownload({json}){
  const [url,setUrl]=useState("");
  useEffect(()=>{
    const file=URL.createObjectURL(new Blob([json],{type:"application/json"}));
    setUrl(file);
    return ()=>URL.revokeObjectURL(file);
  },[json]);
  return url && <a href={url} download="kimodo-reviewed-skeleton.json">생성용 검수 골격 JSON 다운로드</a>;
}

export default function KimodoMultiviewReport(){
  const helpId=useId();
  const [files,setFiles]=useState({}),[report,setReport]=useState(null),[view,setView]=useState(0);
  const [reportRevision,setReportRevision]=useState(0);
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  const [weightsDirty,setWeightsDirty]=useState(false);
  const pending=useRef(null),dirtyRef=useRef(false),submitRef=useRef(null),dirtyNoticeRef=useRef(null),restoreFocus=useRef(false),fileRefs=useRef({});
  useEffect(()=>()=>{pending.current?.abort();pending.current=null;},[]);
  useEffect(()=>{if(!busy && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)(weightsDirty ? dirtyNoticeRef : submitRef).current?.focus();}},[busy,weightsDirty]);
  function changeFile(key,file){
    if(!file || dirtyRef.current || pending.current)return;
    setFiles(current=>({...current,[key]:file}));setReport(null);setError("");
  }
  function removeFile(key,button){
    if(dirtyRef.current || pending.current)return;
    const focused=document.activeElement===button;
    setFiles(current=>{const next={...current};delete next[key];return next;});setReport(null);setError("");
    if(fileRefs.current[key])fileRefs.current[key].value="";
    if(focused)requestAnimationFrame(()=>{if(document.activeElement===document.body)fileRefs.current[key]?.focus();});
  }
  async function load(event){
    event.preventDefault();if(pending.current || dirtyRef.current)return;
    if(!files.observations || !files.skeleton){setError("참조 관절 JSON과 3D 골격 JSON을 모두 선택하세요.");return;}
    restoreFocus.current=document.activeElement===submitRef.current;
    const controller=new AbortController();pending.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");
    try{
      const inputs={};
      for(const [key,file] of Object.entries(files)){
        if(file)inputs[key]=await untilAborted(key==="image"?readReference(file):file.text(),controller.signal);
      }
      const response=await untilAborted(fetch("/management/assistant/kimodo-multiview-report",{method:"POST",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(inputs),signal:controller.signal}),controller.signal);
      const result=await untilAborted(response.json(),controller.signal);
      if(!response.ok)throw new Error(result.detail || "검수 보고서를 불러올 수 없습니다.");
      if(!result || !Array.isArray(result.views) || !result.views.length || result.views.some(item=>!item || !Number.isFinite(item.angle) || !Array.isArray(item.rows) || item.rows.some(row=>!Array.isArray(row) || row.some(cell=>typeof cell!=="string"))) || !Array.isArray(result.limitations) || result.limitations.some(item=>typeof item!=="string") || [result.overlay_png,result.bundle_json,result.bundle_error].some(value=>value!=null && typeof value!=="string") || (result.joint_weights!=null && (!Array.isArray(result.joint_weights.views) || result.joint_weights.views.length!==result.views.length || result.joint_weights.views.some((view,index)=>!view || view.observation!==index+1 || !Array.isArray(view.joints) || view.joints.length!==18 || view.joints.some((joint,j)=>!joint || joint.joint!==j || !Number.isFinite(joint.weight) || typeof joint.reason!=="string")))))throw new Error("검수 보고서 형식을 확인할 수 없습니다.");
      if(pending.current!==controller || controller.signal.aborted)return;
      if(dirtyRef.current)throw new Error("조회 중 가중치 편집이 시작되어 기존 보고서와 편집 내용을 유지합니다.");
      setView(0);setReport(result);setReportRevision(value=>value+1);
    }catch(problem){if(pending.current===controller)setError(timedOut ? "검수 보고서 조회 시간이 초과됐습니다. 다시 시도하세요." : problem.message || "검수 보고서를 불러올 수 없습니다.");}
    finally{clearTimeout(timer);if(pending.current===controller){pending.current=null;setBusy(false);}}
  }
  return <details className="kimodo-multiview"><summary>다중 시점 관절 검수</summary>
    {weightsDirty && <p id={helpId+"-locked"} ref={dirtyNoticeRef} tabIndex={-1} role="status" className="kimodo-multiview-focus">가중치 편집을 취소한 뒤 입력을 바꾸거나 보고서를 다시 조회할 수 있습니다. 필요한 경우 먼저 검증된 파일을 다운로드하세요.</p>}
    <form className="kimodo-multiview-form" onSubmit={load}><fieldset disabled={busy || weightsDirty} aria-describedby={weightsDirty ? helpId+"-locked" : undefined}><legend>검수 입력 파일</legend>
      {[["observations","참조 관절 JSON"],["skeleton","3D 골격 JSON"],["heldout","제외 관측 검증 JSON (선택)"]].map(([key,label])=>
        <div key={key}><label>{label} <input ref={node=>{fileRefs.current[key]=node;}} type="file" accept=".json,application/json" required={key!=="heldout" && !files[key]} aria-describedby={files[key] ? helpId+"-"+key : undefined}
          onChange={e=>{changeFile(key,e.target.files[0]);e.target.value="";}}/></label>{files[key] && <small id={helpId+"-"+key} className="reference-image-name">선택한 파일 · {files[key].name}</small>}
          {key==="heldout" && files[key] && <button type="button" onClick={event=>removeFile(key,event.currentTarget)}>제외 관측 파일 제거</button>}</div>)}
      <div><label>원본 참조 이미지 (선택) <input ref={node=>{fileRefs.current.image=node;}} type="file" accept="image/png" aria-describedby={files.image ? helpId+"-image" : undefined}
        onChange={e=>{changeFile("image",e.target.files[0]);e.target.value="";}}/></label>{files.image && <small id={helpId+"-image"} className="reference-image-name">선택한 파일 · {files.image.name}</small>}
        {files.image && <button type="button" onClick={event=>removeFile("image",event.currentTarget)}>참조 이미지 제거</button>}</div>
      <button ref={submitRef}>관절 오차 조회</button>
    </fieldset></form>
    {error && <p role="alert">{error}</p>}
    {busy && <p role="status">관절 검수 보고서를 조회하고 있습니다.</p>}
    {report && (busy || error) && <p role="status">아래는 마지막으로 조회한 보고서입니다.</p>}
    {report && <><label>검수 방향 <select value={view} onChange={e=>setView(Number(e.target.value))}>
      {report.views.map((row,index)=><option key={index} value={index}>관측 {index+1} · {row.angle}°</option>)}</select></label>
      {report.overlay_png && <figure><img alt="8방향 관절 검출과 재투영 겹침" style={{maxWidth:"100%"}}
        src={"data:image/png;base64,"+report.overlay_png}/><figcaption>8방향 전체 · 초록색은 검출 관절, 보라색은 3D 재투영 관절</figcaption></figure>}
      <ResultTable table={{title:"방향별 관절 검수",columns:["관절","검출 점수","지정 가중치","적용 가중치","근거","적합 오차 (px)","제외 관측 오차 (px)"],rows:report.views[view].rows}}/>
      {report.bundle_json && <BundleDownload json={report.bundle_json}/>}
      {report.bundle_error && <p>생성용 골격 검증 결과 · {report.bundle_error}</p>}
      {report.joint_weights && <KimodoJointWeights key={reportRevision} initial={report.joint_weights} view={view} onViewChange={setView} disabled={busy} onDirtyChange={value=>{dirtyRef.current=value;setWeightsDirty(value);}}/>}
      <details><summary>검수 지표 해석</summary><ul>{report.limitations.map(text=><li key={text}>{text}</li>)}</ul></details></>}
  </details>;
}
