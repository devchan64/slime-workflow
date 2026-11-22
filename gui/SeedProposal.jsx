import React from "react";
import JobIdentifier from "./JobIdentifier.jsx";

export default function SeedProposal({proposal,onOpen}){
  return <section aria-label="시드 변경 생성 제안">{proposal.reason ? <p>{proposal.reason}</p> : <><p>원본 작업</p><JobIdentifier id={proposal.job_id} label="원본 작업 ID" compact/><p>입력을 불러와 {proposal.seed == null ? "다른 시드" : "시드 "+proposal.seed}로 검토합니다. 생성은 확인 후 접수됩니다.</p><button type="button" onClick={()=>onOpen(proposal)}>생성 폼 검토</button></>}</section>;
}
