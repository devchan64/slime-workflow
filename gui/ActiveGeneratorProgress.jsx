import React,{useEffect,useRef,useState} from "react";
import GeneratorSectionCard from "./GeneratorSectionCard.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {useLiveRefresh,LiveRefreshControl} from "./LiveRefresh.jsx";
import GenerationProgress from "./GenerationProgress.jsx";
import JobStatus from "./JobStatus.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import {validGenerationEstimate} from "./generationEstimate.mjs";
import {observedGenerationProgress} from "./generationProgressModel.mjs";
import {validGeneratorHistoryPage} from "./generatorHistoryPage.mjs";

/** 저장된 이력과 읽기 전용 원본 상태로 현재 작업을 관측한다. */
export default function ActiveGeneratorProgress(props){
  return <ActiveGeneratorProgressForService key={props.service} {...props}/>;
}

function ActiveGeneratorProgressForService({service,revision=0,onOpenResult}){
  const [records,setRecords]=useState(null),[error,setError]=useState(''),[refreshKey,refresh]=useState(0),[truncated,setTruncated]=useState(false),[checkedAt,setCheckedAt]=useState(null);
  const [loading,setLoading]=useState(true),refreshRef=useRef(null),restoreFocus=useRef(false),jobRefs=useRef(new Map()),refreshLock=useRef(true);
  useEffect(()=>{if(!loading && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body && refreshRef.current?.isConnected)refreshRef.current.focus();}},[loading]);
  function queueRefresh(manual=false){
    if(refreshLock.current)return;
    refreshLock.current=true;if(manual)restoreFocus.current=document.activeElement===refreshRef.current;
    setLoading(true);refresh(n=>n+1);
  }
  const live=useLiveRefresh(()=>queueRefresh(),true);
  useEffect(()=>{
    let active=true,deadline;const controller=new AbortController();
    async function read(){
      if(document.activeElement===refreshRef.current)restoreFocus.current=true;
      refreshLock.current=true;setLoading(true);
      deadline=setTimeout(()=>{controller.abort();if(active){refreshLock.current=false;setError('작업 상태 조회 시간이 초과됐습니다. 다시 조회하세요.');setLoading(false);}},25000);
      try{
        let offset=0,snapshot=null,total=null,next=null,rows=[],pages=0,missing=false,uncertain=false;const seen=new Set();
        do{
          const payload={limit:30,offset};if(snapshot)payload.snapshot=snapshot;
          const page=await untilAborted(managementCommand(service,'history-observe',payload,{signal:controller.signal}),controller.signal);
          if(!validGeneratorHistoryPage(page,offset,30,snapshot) || (total!==null && page.total!==total) || !Number.isSafeInteger(page.unavailable_count) || page.unavailable_count<0)throw new Error('작업 이력을 확인할 수 없습니다.');
          for(const row of page.records){
            if(!row || typeof row.id!=='string' || !/^[A-Za-z0-9_-]{1,80}$/.test(row.id) || !['job','index','unavailable'].includes(row.status_source) || !['queued','running','completed','failed','cancelled','canceled','paused','unknown'].includes(row.recorded_status) || seen.has(row.id))throw new Error('작업 이력을 확인할 수 없습니다.');
            seen.add(row.id);
          }
          if(!snapshot)snapshot=page.snapshot;
          if(total===null)total=page.total;
          missing ||= (page.unavailable_count || 0)>0;
          uncertain ||= page.records.some(row=>row.status_source!=='job' || row.recorded_status==='unknown');
          rows.push(...page.records.filter(row=>['running','queued'].includes(row.recorded_status) && row.status_source==='job'));
          next=page.next_offset;
          offset=next;pages++;
        }while(next!==null && pages<10);
        const results=new Array(rows.length);let cursor=0;
        async function readStatuses(){
          while(!controller.signal.aborted && cursor<rows.length){
            const index=cursor++,row=rows[index];
            try{
              const response=await untilAborted(managementCommand('hermes-agent','hermes-video-source-status',{service,job_id:row.id},{signal:controller.signal}),controller.signal);
              if(response.service!==service || response.job_id!==row.id || !response.job || !['running','queued','completed','failed','cancelled','canceled','paused'].includes(response.job.status))throw new Error();
              results[index]={id:row.id,job:response.job};
            }catch{results[index]={id:row.id,error:true};}
          }
        }
        await Promise.all(Array.from({length:Math.min(4,rows.length)},()=>readStatuses()));
        if(active && !controller.signal.aborted){
          const visibleResults=results.filter(item=>item.error || ['running','queued'].includes(item.job.status));
          const visibleIds=new Set(visibleResults.map(item=>item.id));
          for(const [id,node] of jobRefs.current)if(!visibleIds.has(id) && node.contains(document.activeElement))restoreFocus.current=true;
          setRecords(visibleResults);setTruncated(next!==null || missing>0 || uncertain);setCheckedAt(new Date());setError('');
        }
      }catch{if(active && !controller.signal.aborted)setError('작업 상태를 확인하지 못했습니다. 다시 조회하세요.');}finally{clearTimeout(deadline);if(active && !controller.signal.aborted){refreshLock.current=false;setLoading(false);}}
    }
    read();return()=>{active=false;refreshLock.current=false;clearTimeout(deadline);controller.abort();};
  },[service,revision,refreshKey]);
  const activeSummary=(error ? '조회 실패 · 마지막 상태 확인 필요' : records===null ? '확인 중' : records.length===0 ? (truncated ? '일부 상태 확인 필요' : '진행 중인 작업 없음') : records.map(item=>{if(item.error)return `${item.id} 상태 확인 불가`;const progress=observedGenerationProgress(item.job);return `${item.id} ${item.job.status==='running'?'실행':'대기'}${progress ? ` · 단계 ${progress.step}/${progress.total}` : ''}`;}).join(' · ') + (truncated ? ' · 일부 상태 확인 필요' : '')) + (checkedAt ? ` · 조회 ${checkedAt.toLocaleTimeString('ko-KR',{timeZone:'Asia/Seoul',hour12:false})}` : '');
  return <GeneratorSectionCard cardRef={live.ref} className="active-generator-progress" title="현재 생성 작업" summary={activeSummary} defaultOpen>
    <div className="active-generator-progress-heading"><button ref={refreshRef} type="button" disabled={loading} onClick={()=>queueRefresh(true)}>{loading?'조회 중…':'상태 새로고침'}</button></div>
    {loading && records!==null && <p role="status">작업 상태를 다시 조회하고 있습니다. 아래는 마지막 조회 결과입니다.</p>}
    <LiveRefreshControl live={live} label="진행 상황 자동 갱신"/>
    {error && <p role="alert">{error}{records && ' 아래는 마지막 조회 결과입니다.'}</p>}
    {truncated && <p role="status">일부 이력을 확인하지 못했습니다. 전체 이력에서 작업을 확인하세요.</p>}
    {records===null ? !error && <p role="status">작업 상태 확인 중…</p> : records.length===0 ? <p>{truncated ? '확인된 이력에 진행 중인 생성 작업이 없습니다.' : '진행 중인 생성 작업 없음'}</p> : records.map(item=><div className="active-generator-job" key={item.id} ref={node=>{if(node)jobRefs.current.set(item.id,node);else jobRefs.current.delete(item.id);}}>
      <div className="active-generator-job-heading"><JobIdentifier id={item.id} compact/>{item.job && <JobStatus state={item.job.status}/>}<button type="button" aria-label={item.id+" 작업 결과 보기"} onClick={()=>onOpenResult(item.id)}>작업 결과 보기</button></div>
      {item.error ? <p role="alert">이 작업의 현재 상태를 확인하지 못했습니다.</p> : <GenerationProgress job={{...item.job,estimate:validGenerationEstimate(item.job.estimate)?item.job.estimate:null}} supportsProgress showQueryTime={false} referenceTime={checkedAt}/>}
    </div>)}
  </GeneratorSectionCard>;
}
