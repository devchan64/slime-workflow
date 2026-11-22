import React,{useEffect,useRef,useState} from "react";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import {managementCommand} from "./managementCommand.js";
import {useLiveRefresh,LiveRefreshControl} from "./LiveRefresh.jsx";
import GenerationProgress from "./GenerationProgress.jsx";
import JobStatus from "./JobStatus.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import {validGenerationEstimate} from "./generationEstimate.mjs";
import {observedGenerationProgress} from "./generationProgressModel.mjs";

/** 저장된 이력과 읽기 전용 원본 상태로 현재 작업을 관측한다. */
export default function ActiveGeneratorProgress({service,revision=0,onOpenResult}){
  const [records,setRecords]=useState(null),[error,setError]=useState(''),[refreshKey,refresh]=useState(0),[truncated,setTruncated]=useState(false),[checkedAt,setCheckedAt]=useState(null);
  const [loading,setLoading]=useState(true),refreshRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>{if(!loading && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body && refreshRef.current?.isConnected)refreshRef.current.focus();}},[loading]);
  const live=useLiveRefresh(()=>refresh(n=>n+1),true);
  useEffect(()=>{
    let active=true,deadline;const controller=new AbortController();
    async function read(){
      if(document.activeElement===refreshRef.current)restoreFocus.current=true;
      setLoading(true);
      deadline=setTimeout(()=>{controller.abort();if(active){setError('작업 상태 조회 시간이 초과됐습니다. 다시 조회하세요.');setLoading(false);}},25000);
      try{
        let offset=0,snapshot=null,next=null,rows=[],pages=0,missing=0,uncertain=false;
        do{
          const payload={limit:30,offset};if(snapshot)payload.snapshot=snapshot;
          const page=await managementCommand(service,'history-observe',payload,{signal:controller.signal});
          if(!Array.isArray(page.records) || typeof page.snapshot!=='string')throw new Error('작업 이력을 확인할 수 없습니다.');
          if(!snapshot)snapshot=page.snapshot;
          missing=page.unavailable_count || 0;
          uncertain ||= page.records.some(row=>row.status_source!=='job' || row.recorded_status==='unknown');
          rows.push(...page.records.filter(row=>['running','queued'].includes(row.recorded_status) && row.status_source==='job'));
          next=page.next_offset;
          if(next!==null && (!Number.isInteger(next) || next<=offset))throw new Error('이력 페이지 정보를 확인할 수 없습니다.');
          offset=next;pages++;
        }while(next!==null && pages<10);
        const results=await Promise.all(rows.map(async row=>{
          try{
            const response=await managementCommand('hermes-agent','hermes-video-source-status',{service,job_id:row.id},{signal:controller.signal});
            if(response.service!==service || response.job_id!==row.id || !response.job || !['running','queued','completed','failed','cancelled','canceled','paused'].includes(response.job.status))throw new Error();
            return {id:row.id,job:response.job};
          }catch{return {id:row.id,error:true};}
        }));
        if(active && !controller.signal.aborted){setRecords(results.filter(item=>item.error || ['running','queued'].includes(item.job.status)));setTruncated(next!==null || missing>0 || uncertain);setCheckedAt(new Date());setError('');}
      }catch{if(active && !controller.signal.aborted)setError('작업 상태를 확인하지 못했습니다. 다시 조회하세요.');}finally{clearTimeout(deadline);if(active && !controller.signal.aborted)setLoading(false);}
    }
    read();return()=>{active=false;clearTimeout(deadline);controller.abort();};
  },[service,revision,refreshKey]);
  const activeSummary=(error ? '조회 실패 · 마지막 상태 확인 필요' : records===null ? '확인 중' : records.length===0 ? (truncated ? '일부 상태 확인 필요' : '진행 중인 작업 없음') : records.map(item=>{if(item.error)return `${item.id} 상태 확인 불가`;const progress=observedGenerationProgress(item.job);return `${item.id} ${item.job.status==='running'?'실행':'대기'}${progress ? ` · 단계 ${progress.step}/${progress.total}` : ''}`;}).join(' · ') + (truncated ? ' · 일부 상태 확인 필요' : '')) + (checkedAt ? ` · 조회 ${checkedAt.toLocaleTimeString('ko-KR',{timeZone:'Asia/Seoul',hour12:false})}` : '');
  return <section ref={live.ref} className="active-generator-progress" aria-label="현재 생성 작업">
    <GeneratorSectionCard title="현재 생성 작업" summary={activeSummary} defaultOpen>
    <div className="active-generator-progress-heading"><button ref={refreshRef} type="button" disabled={loading} onClick={()=>{restoreFocus.current=true;setLoading(true);refresh(n=>n+1);}}>{loading?'조회 중…':'상태 새로고침'}</button></div>
    {loading && records!==null && <p role="status">작업 상태를 다시 조회하고 있습니다. 아래는 마지막 조회 결과입니다.</p>}
    <LiveRefreshControl live={live} label="진행 상황 자동 갱신"/>
    {error && <p role="alert">{error}{records && ' 아래는 마지막 조회 결과입니다.'}</p>}
    {truncated && <p role="status">일부 이력을 확인하지 못했습니다. 전체 이력에서 작업을 확인하세요.</p>}
    {records===null ? !error && <p role="status">작업 상태 확인 중…</p> : records.length===0 ? <p>진행 중인 생성 작업 없음</p> : records.map(item=><div className="active-generator-job" key={item.id}>
      <div className="active-generator-job-heading"><JobIdentifier id={item.id} compact/>{item.job && <JobStatus state={item.job.status}/>}<button type="button" onClick={()=>onOpenResult(item.id)}>작업 결과 보기</button></div>
      {item.error ? <p role="alert">이 작업의 현재 상태를 확인하지 못했습니다.</p> : <GenerationProgress job={{...item.job,estimate:validGenerationEstimate(item.job.estimate)?item.job.estimate:null}} supportsProgress showQueryTime={false} referenceTime={checkedAt}/>}
    </div>)}
    </GeneratorSectionCard>
  </section>;
}
