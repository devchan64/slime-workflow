import React,{useState} from "react";
import ResultTable from "./ResultTable.jsx";

export default function KimodoMultiviewReport(){
  const [files,setFiles]=useState({}),[report,setReport]=useState(null),[view,setView]=useState(0);
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  async function load(event){
    event.preventDefault();setBusy(true);setError("");setReport(null);
    try{
      const inputs={};
      for(const [key,file] of Object.entries(files)){
        if(file)inputs[key]=JSON.parse(await file.text());
      }
      const response=await fetch("/management/assistant/kimodo-multiview-report",{method:"POST",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(inputs)});
      const result=await response.json();
      if(!response.ok)throw new Error(result.detail || "검수 보고서를 불러올 수 없습니다.");
      setView(0);setReport(result);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <details><summary>다중 시점 관절 검수</summary>
    <form onSubmit={load}><fieldset disabled={busy}>
      {[["observations","참조 관절 JSON"],["skeleton","3D 골격 JSON"],["heldout","제외 관측 검증 JSON (선택)"]].map(([key,label])=>
        <label key={key}>{label} <input type="file" accept=".json,application/json" required={key!=="heldout"}
          onChange={e=>{setFiles({...files,[key]:e.target.files[0]});setReport(null);setError("");}}/></label>)}
      <button>관절 오차 조회</button>
    </fieldset></form>
    {error && <p role="alert">{error}</p>}
    {report && <><label>검수 방향 <select value={view} onChange={e=>setView(Number(e.target.value))}>
      {report.views.map((row,index)=><option key={index} value={index}>관측 {index+1} · {row.angle}°</option>)}</select></label>
      <ResultTable table={{title:"방향별 관절 검수",columns:["관절","검출 점수","지정 가중치","적용 가중치","근거","적합 오차 (px)","제외 관측 오차 (px)"],rows:report.views[view].rows}}/>
      <details><summary>검수 지표 해석</summary><ul>{report.limitations.map(text=><li key={text}>{text}</li>)}</ul></details></>}
  </details>;
}
