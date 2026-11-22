import React, {useEffect,useRef,useState} from "react";

export default function GpuQueueSummary() {
  const [gpu,setGpu]=useState("GPU 대기열 조회 중…");
  const [failed,setFailed]=useState(false),[revision,setRevision]=useState(0);
  const [checkedAt,setCheckedAt]=useState(null),[loading,setLoading]=useState(true);
  const statusRef=useRef(null);
  useEffect(()=>{
    const controller=new AbortController();
    let timedOut=false,active=true;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setFailed(false);setLoading(true);setCheckedAt(null);
    setGpu("GPU 대기열 조회 중…");
    fetch("/management/gpu-queue",{signal:controller.signal,cache:"no-store"}).then(async response=>{
      if(!response.ok)throw new Error();
      const data=await response.json();
      if(!Array.isArray(data.jobs)||!["idle","busy","unavailable"].includes(data.gpu_status?.status))throw new Error();
      if(!controller.signal.aborted){setGpu(({busy:"GPU 사용 중",idle:"GPU 유휴",unavailable:"GPU 상태 확인 불가"}[data.gpu_status.status])+" · 대기 작업 "+data.jobs.length+"건"+(data.truncated?" 이상":""));setCheckedAt(new Date());setFailed(data.gpu_status.status==="unavailable");}
    }).catch(()=>{if(active && (!controller.signal.aborted || timedOut)){setGpu(timedOut ? "GPU 대기열 조회 시간이 초과됐습니다." : "GPU 상태 확인 불가");setFailed(true);}}).finally(()=>{clearTimeout(timeout);if(active)setLoading(false);});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[revision]);
  return <div className="gpu-queue-summary"><p ref={statusRef} role="status" tabIndex={-1}>{gpu}{checkedAt && <> · 조회 <time dateTime={checkedAt.toISOString()}>{checkedAt.toLocaleTimeString("ko-KR",{timeZone:"Asia/Seoul",hour12:false})}</time></>}</p>{!loading && <button type="button" onClick={()=>{statusRef.current?.focus({preventScroll:true});setRevision(value=>value+1);}}>{failed ? "GPU 상태 다시 조회" : "GPU 상태 갱신"}</button>}</div>;
}
