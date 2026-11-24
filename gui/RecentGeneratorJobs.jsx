import React,{useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import JobIdentifier from "./JobIdentifier.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import KimodoFrames from "./KimodoFrames.jsx";
import QueuePagination from "./QueuePagination.jsx";
import {sessionQueueStateLabel} from "./sessionQueueValidation.mjs";
import {selectRecentHistorySources,validRecentHistoryPage} from "./recentHistorySource.mjs";
export {validRecentHistorySource} from "./recentHistorySource.mjs";

const labels={queued:"대기 중",running:"실행 중",completed:"완료",failed:"실패",cancelled:"취소",canceled:"취소",paused:"일시 중지",unknown:"확인 불가"};
function category(source){
  if(source.service==="prompt-translation")return "translation";
  if(source.result_kind==="audio")return "audio";
  if(source.service==="kimodo" || source.video_result || source.service==="character-animation")return "motion";
  if(["image","flux"].includes(source.result_kind))return "image";
  return "";
}
function matches(row,filters){
  const {source,record}=row, id=record.id, state=record.recorded_status==="canceled"?"cancelled":record.recorded_status;
  return !filters.run_id && (!filters.category || category(source)===filters.category) && (!filters.state || state===filters.state) &&
    (!filters.generator || source.service.toLowerCase().includes(filters.generator.trim().toLowerCase())) && (!filters.job_id || id.toLowerCase().includes(filters.job_id.trim().toLowerCase())) &&
    (!filters.created_from || id.slice(0,10)>=filters.created_from) && (!filters.created_through || id.slice(0,10)<=filters.created_through);
}

export function RecentJobResult({source,id,choose,onDeleted}){
  return source.service==='kimodo' ? <KimodoFrames key={id} id={id} choose={choose} onDeleted={onDeleted}/> : <MediaJobResult key={source.service+'/'+id} service={source.service} id={id} kind={source.result_kind} folderLink/>;
}

export default function RecentGeneratorJobs({session,filters,filterSummary,revision,choose}){
  const [rows,setRows]=useState([]),[errors,setErrors]=useState([]),[loading,setLoading]=useState(true),[checked,setChecked]=useState(null),[selected,setSelected]=useState(null);
  const [listUnavailable,setListUnavailable]=useState(false),[errorsOpen,setErrorsOpen]=useState(false);
  const [page,setPage]=useState(0),[pageSize,setPageSize]=useState(5),[refreshRevision,refresh]=useState(0);
  const resultRef=useRef(null),triggerRef=useRef(null),headingRef=useRef(null),refreshRef=useRef(null),restoreRefreshFocus=useRef(false);
  useEffect(()=>{if(!loading && restoreRefreshFocus.current){restoreRefreshFocus.current=false;if(document.activeElement===document.body)refreshRef.current?.focus();}},[loading]);
  function closeResult(){
    const previous=document.activeElement;
    setSelected(null);
    requestAnimationFrame(()=>{if(document.activeElement!==document.body && document.activeElement!==previous)return;if(triggerRef.current?.isConnected)triggerRef.current.focus();else headingRef.current?.focus();});
  }
  useEffect(()=>{
    if(!selected || !resultRef.current)return;
    resultRef.current.focus({preventScroll:true});
    resultRef.current.scrollIntoView({block:"start",inline:"nearest"});
  },[selected]);
  useEffect(()=>{setPage(0);setSelected(null);},[filters]);
  useEffect(()=>{
    let active=true;
    const controllers=new Set();
    async function boundedRequest(operation){
      const controller=new AbortController();controllers.add(controller);let timedOut=false;
      const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      try{return await untilAborted(operation(controller.signal),controller.signal);}
      catch(error){if(timedOut)throw new Error('조회 시간이 초과됐습니다.');throw error;}
      finally{clearTimeout(timeout);controllers.delete(controller);}
    }
    async function load(){
      setLoading(true);setErrors([]);
      try{
        const sources=await boundedRequest(async signal=>{
          const response=await fetch('/management/assistant/history-services',{cache:'no-store',signal});
          if(!response.ok)throw new Error('생성기 목록 조회 실패');
          return response.json();
        });
        const eligible=selectRecentHistorySources(sources);
        const collected=[],failed=[];let cursor=0,succeeded=0;
        async function worker(){
          while(active && cursor<eligible.length){
            const source=eligible[cursor++];
            try{
              let page;
              for(let attempt=0;attempt<3;attempt++){
                try{page=await boundedRequest(signal=>managementCommand('hermes-agent',source.command,{service:source.service,limit:10},{signal}));break;}
                catch(error){
                  if(attempt===2 || !(error instanceof Error) || !error.message.includes('해당 원본 이력을 조회 중입니다'))throw error;
                  await new Promise(resolve=>setTimeout(resolve,500));
                  if(!active)return;
                }
              }
              if(!validRecentHistoryPage(page,source.service))throw new Error('이력 응답 오류');
              succeeded++;
              let invalid=0;
              for(const record of page.records){if(record && typeof record.recorded_status==='string' && typeof record.id==='string' && /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(record.id))collected.push({source,record});else invalid++;}
              if(invalid)failed.push({service:source.service,reason:`형식을 확인할 수 없는 기록 ${invalid}건`});
              if(page.unavailable_count)failed.push({service:source.service,reason:`확인할 수 없는 기록 ${page.unavailable_count}건`});
            }catch(error){failed.push({service:source.service,reason:error instanceof Error ? error.message : '이력을 조회할 수 없습니다.'});}
          }
        }
        await Promise.all(Array.from({length:Math.min(4,eligible.length)},()=>worker()));
        if(active){setErrors(failed);if(succeeded===0){setListUnavailable(true);}else{setRows(collected.sort((a,b)=>b.record.id.localeCompare(a.record.id)));setChecked(new Date());setListUnavailable(false);}}
      }catch(error){if(active){setErrors([{service:'생성기 목록',reason:error instanceof Error ? error.message : '목록을 조회할 수 없습니다.'}]);setListUnavailable(true);}}
      finally{if(active)setLoading(false);}
    }
    load();return()=>{active=false;controllers.forEach(controller=>controller.abort());};
  },[revision,refreshRevision]);
  const matching=rows.filter(row=>matches(row,filters)).slice(0,20);
  const currentPage=Math.min(page,Math.max(0,Math.ceil(matching.length/pageSize)-1));
  useEffect(()=>{if(page!==currentPage)setPage(currentPage);},[page,currentPage]);
  return <section aria-label="전체 생성기 최근 작업" className="recent-generator-jobs"><div className="recent-jobs-heading"><h3 ref={headingRef} tabIndex={-1}>전체 생성기 최근 작업</h3><button ref={refreshRef} type="button" disabled={loading} onClick={()=>{restoreRefreshFocus.current=true;refresh(value=>value+1);}}>{loading?"조회 중…":"최근 작업 새로고침"}</button></div>
    <p className="queue-filter-summary">적용된 조건 · {filterSummary || "전체"}</p>
    <p>세션 외 작업도 포함 · 생성기별 최근 10건 중 최대 20건 · 기록 상태 기준{checked && ' · 조회 '+checked.toLocaleString('ko-KR')}</p>
    {loading && <p role="status">최근 작업 조회 중…{checked && " 아래에는 이전 조회 결과가 표시됩니다."}</p>}
    {listUnavailable && checked && <p role="status">최근 작업을 조회하지 못해 이전 결과를 표시합니다. 최근 작업 새로고침으로 다시 확인하세요.</p>}
    {errors.length>0 && <div>{!(listUnavailable && checked) && <p role="status">{listUnavailable ? "최근 작업을 확인하지 못했습니다" : "일부 이력을 확인하지 못했습니다"} · {errors.length}곳</p>}<details open={errorsOpen} onToggle={event=>setErrorsOpen(event.currentTarget.open)}><summary>조회 실패 원인과 조치</summary><p>문제를 확인한 뒤 최근 작업을 새로고침하세요.</p><ul>{errors.map(({service,reason},index)=><li key={service+"/"+index}>{service} · {reason}{service==='writer-agent' && reason.includes('문서 폴더') && <> 운영자에게 <code>.local/writer-agent/workspace.yaml</code>의 문서 폴더 설정과 접근 권한 확인을 요청하세요.</>}</li>)}</ul></details></div>}
    {!loading && !matching.length && !listUnavailable && <p>{errors.length ? "확인된 이력에는 조건에 맞는 최근 작업이 없습니다. 조회하지 못한 이력은 포함되지 않았습니다." : "조건에 맞는 최근 작업이 없습니다."}</p>}
    <div className="session-job-list">{matching.slice(currentPage*pageSize,(currentPage+1)*pageSize).map(({source,record})=><article className="session-job" key={source.service+'/'+record.id}>
      <div className="session-job-heading"><strong>{source.service}</strong><span>기록 · {sessionQueueStateLabel(labels,record.recorded_status)}</span></div>
      <JobIdentifier id={record.id} compact/>
      <div className="session-job-actions">
        {(source.result_kind || source.service==='kimodo') && <button type="button" aria-label={record.id+(selected?.source.service===source.service && selected?.id===record.id ? " 결과 닫기" : " 상태·결과 보기")} aria-expanded={selected?.source.service===source.service && selected?.id===record.id} onClick={event=>{if(selected?.source.service===source.service && selected?.id===record.id)closeResult();else{triggerRef.current=event.currentTarget;setSelected({source,id:record.id});}}}>{selected?.source.service===source.service && selected?.id===record.id ? "결과 닫기" : "상태·결과 보기"}</button>}
        {source.result_path && <a aria-label={record.id+" 생성기에서 열기"} href={source.result_path+'?'+new URLSearchParams({job:record.id,session})}>생성기에서 열기</a>}
      </div>
    </article>)}</div>
    {matching.length>0 && <QueuePagination label="전체 생성기 최근 작업 페이지" page={currentPage} size={pageSize} total={matching.length} onPage={value=>{setSelected(null);setPage(value);}} onPageFocus={()=>headingRef.current?.focus()} onSize={value=>{setSelected(null);setPageSize(value);setPage(0);}}/>}
    {selected && <section ref={resultRef} tabIndex={-1} aria-label="최근 작업 결과"><button type="button" onClick={closeResult}>결과 닫기</button><RecentJobResult source={selected.source} id={selected.id} choose={choose} onDeleted={()=>{setSelected(null);refresh(value=>value+1);}}/></section>}
  </section>;
}
