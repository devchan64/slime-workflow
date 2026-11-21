import React, {useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";

export default function WriterResult({id}) {
  const [detail,setDetail]=useState(null);
  const [error,setError]=useState("");
  const [revision,refresh]=useState(0);
  useEffect(()=>{
    let active=true;
    setError("");setDetail(null);
    managementCommand("writer-agent","writer-detail",{id}).then(record=>{
      if(record.id!==id)throw new Error("선택한 작가 작업과 조회 결과가 일치하지 않습니다.");
      if(active)setDetail(record);
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[id,revision]);
  const proposal=detail?.proposal;
  return <section aria-label="작가 작업 결과"><h3>{id}</h3>
    <button onClick={()=>refresh(value=>value+1)}>결과 새로고침</button>
    {error && <p role="alert">{error}</p>}
    {detail && <>
      <p role="status">{detail.status.stage} · {detail.status.error || detail.status.summary}</p>
      {proposal?.reason && <p>{proposal.reason}</p>}
      {proposal?.changes?.map(change=><details key={change.path}><summary>{change.path}</summary><pre>{change.diff}</pre></details>)}
      {Object.entries({"실행 입력":detail.request,"검토 범위":proposal?.coverage,"탐색 근거":proposal?.evidence,
        "경고":proposal?.warnings,"보존 판단":proposal?.retained,"적용 결과":detail.application,"검색 결과":detail.search,"실행 로그":detail.log})
        .filter(([,value])=>value!=null).map(([label,value])=><details key={label}><summary>{label}</summary>
          <pre>{typeof value==="string"?value:JSON.stringify(value,null,2)}</pre></details>)}
    </>}
  </section>;
}
