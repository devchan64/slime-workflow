import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";

export default function BillboardRegistration({onSaved}){
  const [file,setFile]=useState(null),[review,setReview]=useState(null);
  const [busy,setBusy]=useState(false),[message,setMessage]=useState("");
  async function preview(){
    setBusy(true);setMessage("");setReview(null);
    try{
      const response=await fetch("/management/assistant/billboard-registration-review",{
        method:"POST",headers:{"Content-Type":"application/json"},body:file
      });
      const result=await response.json();
      if(!response.ok)throw new Error(result.error || "등록 요청을 확인할 수 없습니다.");
      setReview(result);
    }catch(problem){setMessage(problem.message);}
    finally{setBusy(false);}
  }
  async function save(){
    setBusy(true);setMessage("");
    try{
      const result=await managementCommand("map-assets","asset-register",review);
      if(!result.asset)throw new Error("등록 결과를 확인할 수 없습니다.");
      setMessage("등록 완료 · "+result.asset);setReview(null);onSaved();
    }catch(problem){setMessage(problem.message);}
    finally{setBusy(false);}
  }
  return <details><summary>신규 빌보드 등록</summary><fieldset disabled={busy}>
    <label>등록 요청 JSON<input type="file" accept=".json,application/json" onChange={e=>{
      setFile(e.target.files[0]);setReview(null);setMessage("");
    }}/></label>
    <button disabled={!file} onClick={preview}>등록 원본 확인</button>
    {review && <section><p>{review.asset.image.path} · {review.asset.image.width} × {review.asset.image.height} px</p>
      <p>접수 {review.requestId} · 예상 DB 세대 {review.expectedGeneration}</p>
      <details><summary>등록 내용</summary><pre>{JSON.stringify(review.asset,null,2)}</pre></details>
      <button onClick={save}>확인 후 신규 등록</button><button onClick={()=>setReview(null)}>등록 취소</button></section>}
    {message && <p role="status">{message}</p>}
  </fieldset></details>;
}
