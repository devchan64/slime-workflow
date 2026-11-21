import React from "react";

const labels=new Map([
  ["queued","대기 중"], ["running","실행 중"], ["completed","완료"],
  ["failed","실패"], ["cancelled","중지됨"], ["canceled","중지됨"],
  ["paused","중단됨"], ["unknown","확인 필요"]
]);

export default function JobStatus({state}) {
  const label=labels.get(state) ?? (typeof state==="string" && state ? "확인 필요 · "+state : "확인 필요");
  return <strong className="job-status" data-state={state}>{label}</strong>;
}
