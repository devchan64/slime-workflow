import React, {useState} from "react";
import {managementCommand} from "./managementCommand.js";

export default function GeneratorJobControls({service,id,state,refresh}) {
  const [review,setReview]=useState(null);
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState("");
  const [log,setLog]=useState(null);
  async function perform(action) {
    setBusy(true);setNotice("");
    try {await action();}
    catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  async function prepareResume() {
    const checked=await managementCommand(service,"resume-preview",{id});
    if(checked.id!==id || checked.service!==service || checked.status!==state ||
        !/^[a-f0-9]{64}$/.test(checked.expected_resume_fingerprint))
      throw new Error("검토한 작업과 상태가 일치하지 않습니다. 상태를 갱신하세요.");
    if(checked.resume_availability && checked.resume_availability!=="available"){
      const reasons={download_running:"모델 다운로드가 진행 중입니다.",other_preparation:"다른 모델 준비 작업이 진행 중입니다."};
      throw new Error(reasons[checked.resume_availability] || "재개 가능 상태를 확인할 수 없습니다.");
    }
    const payload={id,expected_resume_fingerprint:checked.expected_resume_fingerprint};
    if(service==="kimodo"){
      if(checked.keyframe_fingerprint!==null && !/^[a-f0-9]{64}$/.test(checked.keyframe_fingerprint))
        throw new Error("키프레임 확인값을 확인할 수 없습니다.");
      if(checked.resume_availability!=="available")throw new Error("재개 가능 상태를 확인할 수 없습니다.");
      payload.keyframe_fingerprint=checked.keyframe_fingerprint;
    }
    setReview({command:"resume",payload});
  }
  async function confirm() {
    const {command,payload}=review;
    setReview(null);
    await managementCommand(service,service==="kimodo" && command==="resume"?"resume-reviewed":command,payload);
    setNotice(command==="resume"?"재개를 접수했습니다.":"중지를 요청했습니다.");
    refresh();
  }
  return <section aria-label="작업 제어">
    <button disabled={busy} onClick={()=>perform(async()=>{
      const result=await managementCommand(service,"logs",{id});
      setLog(result.log || "기록된 로그가 없습니다.");
    })}>작업 로그 조회</button>
    {log!==null && <pre>{log}</pre>}
    {!review && ["failed","cancelled","paused"].includes(state) &&
      <button disabled={busy} onClick={()=>perform(prepareResume)}>생성 재개 검토</button>}
    {!review && ["queued","running","paused"].includes(state) &&
      <button disabled={busy} onClick={()=>setReview({command:"cancel",payload:{id}})}>작업 중지 검토</button>}
    {review && <section><p>{id} · {review.command==="resume"?"저장된 입력으로 GPU 대기열에 다시 등록합니다.":"선택한 작업에 중지를 요청합니다."}</p>
      <button disabled={busy} onClick={()=>setReview(null)}>취소</button>
      <button disabled={busy} onClick={()=>perform(confirm)}>{review.command==="resume"?"확인 후 재개":"확인 후 중지"}</button>
    </section>}
    <p role="status">{notice}</p>
  </section>;
}
