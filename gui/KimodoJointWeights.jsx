import React,{useEffect,useId,useRef,useState} from "react";
import ResultTable from "./ResultTable.jsx";
import {untilAborted} from "./managementCommand.js";

export default function KimodoJointWeights({initial,view,onViewChange,onDirtyChange,dirty=false,disabled=false,disabledDescriptionId}){
  const errorId=useId(),busyId=useId();
  const [weights,setWeights]=useState(initial),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [download,setDownload]=useState("");
  const [invalidTarget,setInvalidTarget]=useState(null),[focusTarget,setFocusTarget]=useState(null);
  const pending=useRef(null),validateRef=useRef(null),restoreFocus=useRef(false),inputRefs=useRef({});
  useEffect(()=>()=>{if(download)URL.revokeObjectURL(download);},[download]);
  useEffect(()=>()=>{pending.current?.abort();pending.current=null;},[]);
  useEffect(()=>{if(!busy && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body)validateRef.current?.focus();}},[busy]);
  useEffect(()=>{if(focusTarget && focusTarget.view===view){inputRefs.current[focusTarget.joint+":"+focusTarget.field]?.focus();setFocusTarget(null);}},[focusTarget,view]);
  function edit(index,field,value){
    if(pending.current || disabled)return;
    onDirtyChange?.(true);
    setDownload("");
    if(!invalidTarget || (invalidTarget.view===view && invalidTarget.joint===weights.views[view].joints[index].joint && invalidTarget.field===field)){setError("");setInvalidTarget(null);}
    setWeights({...weights,views:weights.views.map((row,i)=>i!==view?row:{...row,joints:row.joints.map((joint,j)=>
      j===index?{...joint,[field]:value}:joint)})});
  }
  function reset(){
    if(pending.current || disabled)return;
    setWeights(initial);setDownload("");setError("");setInvalidTarget(null);onDirtyChange?.(false);
  }
  async function validate(){
    if(pending.current || disabled)return;
    for(const [viewIndex,row] of weights.views.entries())for(const joint of row.joints){
      if(typeof joint.weight!=="number" || !Number.isFinite(joint.weight) || joint.weight<0 || joint.weight>1){setDownload("");setInvalidTarget({view:viewIndex,joint:joint.joint,field:"weight"});setError(`관측 ${viewIndex+1} · ${joint.joint}번 관절의 가중치를 0부터 1까지 입력하세요.`);return;}
      if(!joint.reason.trim()){setDownload("");setInvalidTarget({view:viewIndex,joint:joint.joint,field:"reason"});setError(`관측 ${viewIndex+1} · ${joint.joint}번 관절의 판단 근거를 입력하세요.`);return;}
    }
    setInvalidTarget(null);
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
    }catch(problem){if(pending.current===controller)setError(timedOut ? "가중치 검증 시간이 초과됐습니다. 다시 시도하세요." : problem?.message || "가중치 표를 검증할 수 없습니다. 다시 시도하세요.");}
    finally{clearTimeout(timer);if(pending.current===controller){pending.current=null;setBusy(false);}}
  }
  return <details className="kimodo-joint-weights"><summary>관절 가중치 편집{busy ? " · 검증 중" : error ? " · 오류 확인 필요" : dirty ? " · 편집 중" : ""}</summary><fieldset disabled={busy || disabled} aria-describedby={[busy && busyId,disabled && disabledDescriptionId].filter(Boolean).join(" ") || undefined}><legend className="generator-visually-hidden">관절 가중치 입력</legend>
    <p>각 관절의 가중치는 0부터 1까지 입력하고 판단 근거를 작성하세요. 검증은 모든 관측 방향에 적용됩니다.</p>
    <ResultTable table={{title:"관측 "+(view+1)+" · BODY18 가중치",columns:["관절","가중치","판단 근거"],
      rows:weights.views[view].joints.map(({joint,weight,reason},i)=>[joint,
        <input ref={node=>{inputRefs.current[joint+":weight"]=node;}} aria-label={joint+"번 관절 가중치"} aria-invalid={invalidTarget?.view===view && invalidTarget.joint===joint && invalidTarget.field==="weight" || undefined} aria-describedby={invalidTarget?.view===view && invalidTarget.joint===joint && invalidTarget.field==="weight" ? errorId : undefined} type="number" min="0" max="1" step="any" value={weight}
          onChange={e=>edit(i,"weight",e.target.value===""?"":Number(e.target.value))}/>,
        <input ref={node=>{inputRefs.current[joint+":reason"]=node;}} aria-label={joint+"번 관절 판단 근거"} aria-invalid={invalidTarget?.view===view && invalidTarget.joint===joint && invalidTarget.field==="reason" || undefined} aria-describedby={invalidTarget?.view===view && invalidTarget.joint===joint && invalidTarget.field==="reason" ? errorId : undefined} value={reason} onChange={e=>edit(i,"reason",e.target.value)}/>])}}/>
    <button ref={validateRef} type="button" onClick={validate}>8방향 가중치 검증</button>
    <button type="button" onClick={reset}>가중치 편집 취소</button>
    {download && <a href={download} download="kimodo-joint-weights.json">검증된 가중치 JSON 다운로드</a>}
    {error && <p id={errorId} role="alert">{error}</p>}
    {invalidTarget && <button type="button" onClick={()=>{onViewChange(invalidTarget.view);setFocusTarget(invalidTarget);}}>오류 입력으로 이동</button>}
  </fieldset>{busy && <p id={busyId} role="status">가중치를 검증하고 있습니다.</p>}</details>;
}
