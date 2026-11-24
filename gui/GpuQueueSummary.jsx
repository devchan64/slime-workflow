import React, {useEffect,useState} from "react";
import {untilAborted} from "./managementCommand.js";
import {formatGpuQueueSummary} from "./gpuQueueSummary.mjs";

export default function GpuQueueSummary() {
  const [gpu,setGpu]=useState("");
  const [failed,setFailed]=useState(false),[revision,setRevision]=useState(0);
  const [checkedAt,setCheckedAt]=useState(null),[loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    let timedOut=false,active=true;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setLoading(true);setError("");
    untilAborted((async()=>{
      const response=await fetch("/management/gpu-queue",{signal:controller.signal,cache:"no-store"});
      if(!response.ok)throw new Error();
      const data=await response.json();
      return formatGpuQueueSummary(data);
    })(),controller.signal).then(summary=>{
      if(active){setGpu(summary.text);setCheckedAt(new Date());setFailed(summary.unavailable);}
    }).catch(()=>{if(active){setError(timedOut ? "GPU 대기열 조회 시간이 초과됐습니다." : "GPU 상태를 조회하지 못했습니다.");setFailed(true);}}).finally(()=>{clearTimeout(timeout);if(active)setLoading(false);});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[revision]);
  return <div className="gpu-queue-summary"><p role="status">{loading ? "GPU 대기열 조회 중…" : error || gpu}{(loading || error) && gpu && <> · 마지막 조회 결과: {gpu}</>}{checkedAt && <> · 조회 <time dateTime={checkedAt.toISOString()}>{checkedAt.toLocaleTimeString("ko-KR",{timeZone:"Asia/Seoul",hour12:false})}</time></>}</p><button type="button" aria-disabled={loading} onClick={()=>{if(!loading)setRevision(value=>value+1);}}>{loading ? "GPU 상태 조회 중…" : failed ? "GPU 상태 다시 조회" : "GPU 상태 갱신"}</button></div>;
}
