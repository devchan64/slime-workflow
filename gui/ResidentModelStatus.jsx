import React,{useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";

const descriptions={
  ready:["준비","이 세션의 Qwen 3.8 상주 모델과 GPU 예약이 확인됐습니다."],
  queued:["대기","이 세션의 Qwen 3.8 상주 모델이 GPU 대기열에서 기다리고 있습니다."],
  running:["전환 중","상주 모델이 시작·종료 또는 상태 전환 중입니다. GPU 로딩 완료는 아직 확인되지 않았습니다."],
  released:["해제","이 세션의 Qwen 3.8 상주 모델이 해제됐습니다."],
  not_found:["없음","이 세션에 확인된 상주 모델이 없습니다. 다른 세션의 모델 상태는 포함하지 않습니다."],
  unknown:["확인 불가","이 세션의 Qwen 3.8 상주 모델 상태를 확인할 수 없습니다."],
};

export default function ResidentModelStatus({session}){
  const [snapshot,setSnapshot]=useState(null),[error,setError]=useState(""),[checking,setChecking]=useState(false),[revision,refresh]=useState(0);
  const [saving,setSaving]=useState(false),[saveError,setSaveError]=useState("");
  const refreshRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>{if(!checking && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body && refreshRef.current?.isConnected && refreshRef.current.closest("details")?.open)refreshRef.current.focus();}},[checking]);
  useEffect(()=>{
    let active=true,timer,sequence=0,controller;
    async function read(){
      if(document.visibilityState!=="visible")return;
      clearTimeout(timer);controller?.abort();controller=new AbortController();const current=++sequence,request=controller;
      if(document.activeElement===refreshRef.current)restoreFocus.current=true;
      setChecking(true);
      let deadline;
      try{
        const result=await Promise.race([managementCommand("hermes-agent","hermes-resident-status",{session_id:session},{signal:request.signal}),new Promise((_,reject)=>{deadline=setTimeout(()=>{request.abort();reject(new Error("status timeout"));},10000);})]);
        if(result?.session_id!==session || !result.resident || !Object.hasOwn(descriptions,result.resident.state))throw new Error("invalid status");
        if(result.resident.state==="ready" && (result.resident.model!=="qwen3.8-27b" || result.resident.gpu_loaded!==true || result.resident.reservation_verified!==true))throw new Error("invalid ready status");
        if(active && current===sequence){setSnapshot({state:result.resident.state,dflash:result.dflash_enabled===true,activeDflash:result.resident.dflash===true,checkedAt:new Date()});setError("");}
      }catch(problem){if(active && current===sequence)setError(problem?.message?.startsWith("invalid ") ? "모델 상태 응답을 확인할 수 없습니다. 다시 조회하세요." : problem?.message==="status timeout" || problem?.name==="AbortError" ? "모델 상태 조회 시간이 초과됐습니다. 다시 조회하세요." : "모델 상태 조회 실패 · "+requestErrorMessage(problem));}
      finally{clearTimeout(deadline);if(active && current===sequence){setChecking(false);if(document.visibilityState==="visible")timer=setTimeout(read,30000);}}
    }
    function visibility(){clearTimeout(timer);sequence++;controller?.abort();if(document.visibilityState==="visible")read();else setChecking(false);}
    read();document.addEventListener("visibilitychange",visibility);
    return()=>{active=false;clearTimeout(timer);controller?.abort();document.removeEventListener("visibilitychange",visibility);};
  },[session,revision]);
  async function changeDflash(enabled){
    setSaving(true);setSaveError("");
    try{
      const result=await managementCommand("hermes-agent","hermes-resident-dflash",{session_id:session,enabled},{signal:AbortSignal.timeout(15000)});
      if(result?.enabled!==enabled || result.session_id!==session)throw Error("DFlash2 설정 저장 결과를 확인하세요.");
      setSnapshot(previous=>({...previous,dflash:enabled}));
    }catch(problem){setSaveError(requestErrorMessage(problem));}
    finally{setSaving(false);refresh(value=>value+1);}
  }
  const [label,description]=error ? ["조회 실패",error] : snapshot ? descriptions[snapshot.state] : ["조회 중","이 세션의 상주 모델 상태를 확인하고 있습니다."];
  return <><details name="composer-popover" className="resident-model-status"><summary title={`세션 상주 Qwen 3.8 · ${description}`} aria-label={`세션 상주 Qwen 3.8 · ${label}`}>Qwen 3.8 · <span aria-live="polite">{label}</span></summary><div className="resident-model-status-panel" aria-busy={checking}><p>{description}</p>{snapshot?.state==="ready" && <p>현재 로드된 모델 · DFlash2 {snapshot.activeDflash?"켜짐":"꺼짐"}</p>}{snapshot && <p>마지막 조회 성공 · <time dateTime={snapshot.checkedAt.toISOString()}>{snapshot.checkedAt.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false})}</time>{error && " · 이전 관측"}</p>}<p>이 탭이 보이는 동안 30초 간격으로 조회합니다.</p><button ref={refreshRef} type="button" disabled={checking} onClick={()=>{restoreFocus.current=true;refresh(value=>value+1);}}>{checking ? "조회 중…" : "모델 상태 다시 조회"}</button></div></details>
    <button type="button" aria-pressed={snapshot ? snapshot.dflash : undefined}
      title="이 세션의 다음 모델 로딩부터 적용합니다."
      disabled={!snapshot || saving || Boolean(error)}
      onClick={()=>changeDflash(!snapshot.dflash)}>
      DFlash2 · {saving ? "저장 중" : !snapshot ? "조회 중" : snapshot.dflash ? "켜짐" : "꺼짐"}
    </button>
    {saveError && <span role="alert">{saveError}</span>}
  </>;
}
