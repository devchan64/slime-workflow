import React,{useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {historyInputDetails,historyInputSummary} from "./historyInputSummary.mjs";
import {requestErrorMessage} from "./requestError.mjs";

/** 결과에 저장된 요청을 표시한다. 입력 적용은 별도 사용자 동작이다. */
export default function SavedGeneratorInputs({id,readJob,service,statusCommand}){
  const reader=useRef(readJob);reader.current=readJob;
  const resultRef=useRef(null),restoreFocus=useRef(false);
  const [state,setState]=useState({id,service,statusCommand,loading:true}),[revision,retry]=useState(0);
  useEffect(()=>()=>{restoreFocus.current=false;},[id,service,statusCommand]);
  useEffect(()=>{
    if(!restoreFocus.current || state.id!==id || state.service!==service || state.statusCommand!==statusCommand || state.loading)return;
    restoreFocus.current=false;
    const frame=requestAnimationFrame(()=>{if(document.activeElement===document.body && resultRef.current?.isConnected)resultRef.current.focus();});
    return ()=>cancelAnimationFrame(frame);
  },[state,id,service,statusCommand]);
  useEffect(()=>{
    let active=true,timedOut=false;const controller=new AbortController();
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setState({id,service,statusCommand,loading:true});
    (async()=>{try{
      const result=await untilAborted(reader.current ? reader.current(id) : managementCommand(service,statusCommand,{id},{signal:controller.signal}),controller.signal);
      if(result?.id!==id || !result.request || typeof result.request!=='object' || Array.isArray(result.request))throw new Error('저장 입력이 선택한 작업과 일치하지 않습니다.');
      if(active)setState({id,service,statusCommand,request:result.request});
    }catch(error){if(active)setState({id,service,statusCommand,error:timedOut?'조회 시간이 초과됐습니다.':requestErrorMessage(error)});}finally{clearTimeout(timeout);}})();
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[id,service,statusCommand,revision]);
  if(state.id!==id || state.service!==service || state.statusCommand!==statusCommand || state.loading)return <p role="status">저장 입력을 불러오는 중입니다.</p>;
  if(state.error)return <div><p ref={resultRef} className="saved-generator-inputs-error" tabIndex={-1} role="alert">저장 입력 조회 실패 · {state.error}</p><button type="button" onClick={()=>{restoreFocus.current=true;retry(n=>n+1);}}>입력 정보 다시 조회</button></div>;
  const summary=historyInputSummary(state.request,service);
  const details=historyInputDetails(state.request);
  return <section ref={resultRef} tabIndex={-1} className="history-action-detail saved-generator-inputs" aria-label="저장된 생성 입력"><strong>저장된 생성 입력</strong>{summary.length>0 && <p>{summary.join(' · ')}</p>}<details><summary>저장된 입력 상세</summary><pre>{details}</pre></details></section>;
}
