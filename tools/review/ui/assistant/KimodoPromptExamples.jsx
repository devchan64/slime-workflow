import React,{useState} from "react";

export default function KimodoPromptExamples({apply,applySettings}){
  const [rows,setRows]=useState([]),[id,select]=useState(""),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  async function load(){
    setBusy(true);setError("");
    try{
      const response=await fetch("/management/assistant/kimodo-prompt-examples");
      if(!response.ok)throw new Error("동작 설명 예시를 불러올 수 없습니다.");
      const examples=await response.json();
      setRows(examples);select(examples[0]?.id || "");
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  const selected=rows.find(row=>row.id===id);
  return <section aria-label="동작 설명 예시">
    {!rows.length && <button type="button" disabled={busy} onClick={load}>동작 설명 예시 조회</button>}
    {selected && <><label>동작 설명 예시 <select value={id} onChange={e=>select(e.target.value)}>
      {rows.map(row=><option key={row.id} value={row.id}>{row.label}</option>)}</select></label>
      <pre>{selected.prompt}</pre><button type="button" onClick={()=>apply(selected.prompt)}>동작 설명에 적용</button>
      {applySettings && <button type="button" onClick={()=>applySettings(selected.id)}>예시 설정과 참조 함께 적용</button>}</>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
