import React,{useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {historyInputSummary} from "./historyInputSummary.mjs";
import {requestErrorMessage} from "./requestError.mjs";

/** 결과에 저장된 요청을 표시한다. 입력 적용은 별도 사용자 동작이다. */
export default function SavedGeneratorInputs({id,readJob,service,statusCommand}){
  const reader=useRef(readJob);reader.current=readJob;
  const resultRef=useRef(null),restoreFocus=useRef(false);
  const [state,setState]=useState({id,loading:true}),[revision,retry]=useState(0);
  useEffect(()=>{
    if(!restoreFocus.current || state.id!==id || state.loading)return;
    restoreFocus.current=false;
    requestAnimationFrame(()=>{if(document.activeElement===document.body && resultRef.current?.isConnected)resultRef.current.focus();});
  },[state,id]);
  useEffect(()=>{
    let active=true;setState({id,loading:true});
    (async()=>{try{
      const result=reader.current ? await reader.current(id) : await managementCommand(service,statusCommand,{id});
      if(result?.id!==id || !result.request || typeof result.request!=='object')throw new Error('저장 입력이 선택한 작업과 일치하지 않습니다.');
      if(active)setState({id,request:result.request});
    }catch(error){if(active)setState({id,error:requestErrorMessage(error)});}})();
    return ()=>{active=false;};
  },[id,service,statusCommand,revision]);
  if(state.id!==id || state.loading)return <p role="status">저장 입력을 불러오는 중입니다.</p>;
  if(state.error)return <p ref={resultRef} tabIndex={-1} role="alert">저장 입력 조회 실패 · {state.error} <button type="button" onClick={()=>{restoreFocus.current=true;retry(n=>n+1);}}>입력 정보 다시 조회</button></p>;
  const summary=historyInputSummary(state.request,service);
  const details=JSON.stringify(state.request,(key,value)=>typeof value==='string' && (value.startsWith('data:') || value.length>10000) ? '[첨부 또는 긴 데이터 생략]' : value,2);
  return <section ref={resultRef} tabIndex={-1} className="history-action-detail" aria-label="저장된 생성 입력"><strong>저장된 생성 입력</strong>{summary.length>0 && <p>{summary.join(' · ')}</p>}<details><summary>저장된 입력 상세</summary><pre>{details}</pre></details></section>;
}
