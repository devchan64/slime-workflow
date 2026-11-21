import React, {useState} from "react";

export default function TranslationEvidence({source,call}) {
  const [busy,setBusy]=useState(false);
  const [result,setResult]=useState(null);
  const [error,setError]=useState("");
  async function search() {
    setBusy(true);setResult(null);setError("");
    try {setResult(await call("translation-evidence",{text:source}));}
    catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <details><summary>작가 AI 문서에서 용어 후보 찾기</summary>
    <button disabled={busy || !source.trim()} onClick={search}>원문으로 문서 검색</button>
    {error && <p role="alert">{error}</p>}
    {result && <><p>{result.candidates.length}건 · {result.note}</p>
      {result.candidates.map((item,index)=><section key={index}><strong>{item.heading}</strong>
        <p>{item.path} · {item.matched_terms.join(", ")}</p><p>{item.text}</p></section>)}</>}
  </details>;
}
