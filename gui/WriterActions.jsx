import React, {useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";

export default function WriterActions({onAccepted,onWorkspace}) {
  const [workspace,setWorkspace]=useState(null);
  const [revision,refresh]=useState(0);
  const [prompt,setPrompt]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  useEffect(()=>{
    let active=true,timer;
    function read(){
    managementCommand("writer-agent","writer-state").then(record=>{
      if(active){setWorkspace(record);onWorkspace?.(record.jobs || []);if(record.active_job)timer=setTimeout(read,3000); }
    }).catch(problem=>{if(active)setError(problem.message);});
    }
    read();
    return ()=>{active=false;clearTimeout(timer);};
  },[revision,onWorkspace]);
  function reload() {
    setWorkspace(null);
    refresh(value=>value+1);
  }
  async function submit(mode) {
    setBusy(true);setError("");
    try {
      const payload={mode,prompt:["prepare","learn"].includes(mode)?"":prompt.trim()};
      const record=await managementCommand("writer-agent","writer-submit",payload);
      if(!record?.id)throw new Error("접수 ID를 확인할 수 없습니다. 실행 이력을 조회하세요.");
      onAccepted(record.id);
    } catch(problem) {setError(problem.message);}
    finally {reload();setBusy(false);}
  }
  const prepare=Boolean(workspace?.configured && !workspace.active_job);
  const learn=prepare && workspace.ready;
  const trained=learn && workspace.trained;
  return <fieldset disabled={busy}><legend>작가 작업 요청</legend>
    <button onClick={()=>{setError("");reload();}}>준비 상태 새로고침</button>
    {workspace?.configured && <details><summary>문서·색인·기록 경로</summary><pre>{[workspace.document_root,workspace.index_path,workspace.state_root].join("\n")}</pre></details>}
    {workspace && <p role="status">{workspace.active_job?"진행 중인 작업 "+workspace.active_job:
      !workspace.configured?"먼저 문서 폴더를 연결하세요.":!workspace.ready?"실행 환경을 준비하세요.":
      !workspace.trained?"문서를 학습해 검색 색인을 만드세요.":"작성과 중복 검토를 요청할 수 있습니다."}</p>}
    <button disabled={!prepare} onClick={()=>submit("prepare")}>환경 준비</button>
    <button disabled={!learn} onClick={()=>submit("learn")}>학습 · 색인 갱신</button>
    <label>작성 지시 또는 중복 검토 범위<textarea maxLength={6000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
    <button disabled={!trained || !prompt.trim()} onClick={()=>submit("write")}>작성 제안 요청</button>
    <button disabled={!trained} onClick={()=>submit("deduplicate")}>중복 검토 요청</button>
    <p>중복 검토 범위를 비우면 전체 색인을 검사합니다.</p>
    {error && <p role="alert">{error}</p>}
  </fieldset>;
}
