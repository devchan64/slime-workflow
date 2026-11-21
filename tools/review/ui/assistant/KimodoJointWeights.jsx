import React,{useEffect,useState} from "react";
import ResultTable from "./ResultTable.jsx";

export default function KimodoJointWeights({initial,view}){
  const [weights,setWeights]=useState(initial),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [download,setDownload]=useState("");
  useEffect(()=>()=>{if(download)URL.revokeObjectURL(download);},[download]);
  function edit(index,field,value){
    setDownload("");setError("");
    setWeights({...weights,views:weights.views.map((row,i)=>i!==view?row:{...row,joints:row.joints.map((joint,j)=>
      j===index?{...joint,[field]:value}:joint)})});
  }
  async function validate(){
    setBusy(true);setError("");setDownload("");
    try{
      const response=await fetch("/management/assistant/kimodo-joint-weights",{method:"POST",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(weights)});
      const checked=await response.json();
      if(!response.ok)throw new Error(checked.detail || "가중치 표를 검증할 수 없습니다.");
      setDownload(URL.createObjectURL(new Blob([JSON.stringify(checked,null,2)],{type:"application/json"})));
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <details><summary>관절 가중치 편집</summary><fieldset disabled={busy}>
    <ResultTable table={{title:"관측 "+(view+1)+" · BODY18 가중치",columns:["관절","가중치","판단 근거"],
      rows:weights.views[view].joints.map(({joint,weight,reason},i)=>[joint,
        <input aria-label={joint+"번 관절 가중치"} type="number" min="0" max="1" step="any" value={weight}
          onChange={e=>edit(i,"weight",e.target.value===""?"":Number(e.target.value))}/>,
        <input aria-label={joint+"번 관절 판단 근거"} value={reason} onChange={e=>edit(i,"reason",e.target.value)}/>])}}/>
    <button type="button" onClick={validate}>8방향 가중치 검증</button>
    {download && <a href={download} download="kimodo-joint-weights.json">검증된 가중치 JSON 다운로드</a>}
    {error && <p role="alert">{error}</p>}
  </fieldset></details>;
}
