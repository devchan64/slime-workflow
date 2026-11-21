import React, {useEffect,useState} from "react";

export default function GpuQueueSummary() {
  const [gpu,setGpu]=useState("GPU 대기열 조회 중…");
  useEffect(()=>{
    const controller=new AbortController();
    setGpu("GPU 대기열 조회 중…");
    fetch("/management/gpu-queue",{signal:controller.signal,cache:"no-store"}).then(async response=>{
      if(!response.ok)throw new Error();
      const data=await response.json();
      if(!Array.isArray(data.jobs)||!["idle","busy"].includes(data.gpu_status?.status))throw new Error();
      if(!controller.signal.aborted)setGpu((data.gpu_status.status==="busy"?"GPU 사용 중":"GPU 유휴")+" · 대기 작업 "+data.jobs.length+"건"+(data.truncated?" 이상":""));
    }).catch(()=>{if(!controller.signal.aborted)setGpu("GPU 상태 확인 불가");});
    return ()=>controller.abort();
  },[]);
  return <p role="status">{gpu}</p>;
}
