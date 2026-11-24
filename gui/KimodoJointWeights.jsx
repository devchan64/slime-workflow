import React,{useEffect,useRef,useState} from "react";
import ResultTable from "./ResultTable.jsx";
import {untilAborted} from "./managementCommand.js";

export default function KimodoJointWeights({initial,view,onDirtyChange,disabled=false}){
  const [weights,setWeights]=useState(initial),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [download,setDownload]=useState("");
  const pending=useRef(null),validateRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>()=>{if(download)URL.revokeObjectURL(download);},[download]);
  useEffect(()=>()=>{pending.current?.abort();pending.current=null;},[]);
  useEffect(()=>{if(!busy && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)validateRef.current?.focus();}},[busy]);
  function edit(index,field,value){
    if(pending.current || disabled)return;
    onDirtyChange?.(true);
    setDownload("");setError("");
    setWeights({...weights,views:weights.views.map((row,i)=>i!==view?row:{...row,joints:row.joints.map((joint,j)=>
      j===index?{...joint,[field]:value}:joint)})});
  }
  function reset(){
    if(pending.current || disabled)return;
    setWeights(initial);setDownload("");setError("");onDirtyChange?.(false);
  }
  async function validate(){
    if(pending.current || disabled)return;
    restoreFocus.current=document.activeElement===validateRef.current;
    const controller=new AbortController();pending.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setError("");setDownload("");
    try{
      const response=await untilAborted(fetch("/management/assistant/kimodo-joint-weights",{method:"POST",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(weights),signal:controller.signal}),controller.signal);
      const checked=await untilAborted(response.json(),controller.signal);
      if(!response.ok)throw new Error(checked.detail || "가중치 표를 검증할 수 없습니다.");
      if(!checked || Object.keys(checked).length!==2 || checked.schema!==weights.schema || !Array.isArray(checked.views) || checked.views.length!==weights.views.length || checked.views.some((row,index)=>!row || Object.keys(row).length!==2 || row.observation!==weights.views[index].observation || !Array.isArray(row.joints) || row.joints.length!==weights.views[index].joints.length || row.joints.some((joint,j)=>!joint || Object.keys(joint).length!==3 || ["joint","weight","reason"].some(field=>joint[field]!==weights.views[index].joints[j][field]))))throw new Error("검증된 가중치 응답이 입력과 일치하지 않습니다.");
      if(pending.current!==controller || controller.signal.aborted)return;
      setDownload(URL.createObjectURL(new Blob([JSON.stringify(checked,null,2)],{type:"application/json"})));
    }catch(problem){if(pending.current===controller)setError(timedOut ? "가중치 검증 시간이 초과됐습니다. 다시 시도하세요." : problem.message || "가중치 표를 검증할 수 없습니다.");}
    finally{clearTimeout(timer);if(pending.current===controller){pending.current=null;setBusy(false);}}
  }
  return <details><summary>관절 가중치 편집</summary><fieldset disabled={busy || disabled}>
    <ResultTable table={{title:"관측 "+(view+1)+" · BODY18 가중치",columns:["관절","가중치","판단 근거"],
      rows:weights.views[view].joints.map(({joint,weight,reason},i)=>[joint,
        <input aria-label={joint+"번 관절 가중치"} type="number" min="0" max="1" step="any" value={weight}
          onChange={e=>edit(i,"weight",e.target.value===""?"":Number(e.target.value))}/>,
        <input aria-label={joint+"번 관절 판단 근거"} value={reason} onChange={e=>edit(i,"reason",e.target.value)}/>])}}/>
    <button ref={validateRef} type="button" onClick={validate}>8방향 가중치 검증</button>
    <button type="button" onClick={reset}>가중치 편집 취소</button>
    {download && <a href={download} download="kimodo-joint-weights.json">검증된 가중치 JSON 다운로드</a>}
    {error && <p role="alert">{error}</p>}
    {busy && <p role="status">가중치를 검증하고 있습니다.</p>}
  </fieldset></details>;
}
