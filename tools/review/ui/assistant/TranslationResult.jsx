import React, {useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

export default function TranslationResult({job, text}) {
  const [draft,setDraft] = useState(text);
  const [checks,setChecks] = useState(null);
  const [busy,setBusy] = useState(false);
  const [notice,setNotice] = useState("");
  async function inspect() {
    setBusy(true);setNotice("");
    try {
      const record = await managementCommand("prompt-translation","translation-status",{id:job});
      if (record.id!==job || !record.result) throw new Error("해당 작업의 번역 결과를 확인할 수 없습니다.");
      const {term_checks=[],quality_checks} = record.result;
      const rows = term_checks.map(item=>[item.source,item.target,item.status==="matched"?"일치":"불일치 · 확인 필요",item.source_ref || ""]);
      for (const item of quality_checks || []) {
        rows.push([item.source,item.target,({matched:"표현 발견 · 문맥 확인",reversed:"행·열 역전"})[item.status] || "확인 필요",item.source_ref || ""]);
      }
      setChecks({title:"용어·배치·조건 점검", summary:quality_checks ? "원본 번역 결과 기준" : "이전 작업 · 배치·조건 미검사",
        columns:["원문","번역어","결과","근거"],rows});
    } catch(problem) {setNotice(problem.message);}
    finally {setBusy(false);}
  }
  async function copy() {
    try {await navigator.clipboard.writeText(draft);setNotice("번역문을 복사했습니다.");}
    catch {setNotice("번역문을 선택해 복사하세요.");}
  }
  return <section><label>복사용 번역문 <textarea value={draft} onChange={e=>setDraft(e.target.value)}/></label>
    <button onClick={copy}>번역문 복사</button>
    <button disabled={busy} onClick={inspect}>원본 번역 점검 조회</button>
    {checks && <ResultTable table={checks}/>}
    <p role="status">{notice}</p>
  </section>;
}
