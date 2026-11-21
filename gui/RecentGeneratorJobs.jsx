import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import JobIdentifier from "./JobIdentifier.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import QueuePagination from "./QueuePagination.jsx";

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
    (!filters.generator || source.service.includes(filters.generator.trim())) && (!filters.job_id || id.includes(filters.job_id.trim())) &&
    (!filters.created_from || id.slice(0,10)>=filters.created_from) && (!filters.created_through || id.slice(0,10)<=filters.created_through);
}

export default function RecentGeneratorJobs({session,filters,revision}){
  const [rows,setRows]=useState([]),[errors,setErrors]=useState([]),[loading,setLoading]=useState(true),[checked,setChecked]=useState(null),[selected,setSelected]=useState(null);
  const [page,setPage]=useState(0),[pageSize,setPageSize]=useState(5);
  useEffect(()=>setPage(0),[filters]);
  useEffect(()=>{
    let active=true;
    async function load(){
      setLoading(true);setErrors([]);
      try{
        const response=await fetch('/management/assistant/history-services',{cache:'no-store'});
        if(!response.ok)throw new Error('생성기 목록 조회 실패');
        const sources=await response.json();
        if(!Array.isArray(sources))throw new Error('생성기 목록 형식 오류');
        const eligible=sources.filter(s=>s && typeof s.service==='string' && ['hermes-generator-source-history','hermes-audio-source-history'].includes(s.command));
        const collected=[],failed=[];let cursor=0;
        async function worker(){
          while(cursor<eligible.length){
            const source=eligible[cursor++];
            try{
              const page=await managementCommand('hermes-agent',source.command,{service:source.service,limit:10});
              if(page.service!==source.service || !Array.isArray(page.records))throw new Error('이력 응답 오류');
              for(const record of page.records)if(typeof record.id==='string' && /^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(record.id))collected.push({source,record});
              if(page.unavailable_count)failed.push(source.service+' 일부 기록');
            }catch{failed.push(source.service);}
          }
        }
        await Promise.all(Array.from({length:Math.min(4,eligible.length)},()=>worker()));
        if(active){setRows(collected.sort((a,b)=>b.record.id.localeCompare(a.record.id)));setErrors(failed);setChecked(new Date());}
      }catch{if(active){setRows([]);setErrors(['생성기 목록']);setChecked(new Date());}}
      finally{if(active)setLoading(false);}
    }
    load();return()=>{active=false;};
  },[revision]);
  const matching=rows.filter(row=>matches(row,filters)).slice(0,20);
  const currentPage=Math.min(page,Math.max(0,Math.ceil(matching.length/pageSize)-1));
  return <section aria-label="전체 생성기 최근 작업" className="recent-generator-jobs"><h3>전체 생성기 최근 작업</h3>
    <p>세션 외 작업도 포함 · 생성기별 최근 10건 중 최대 20건 · 기록 상태 기준{checked && ' · 조회 '+checked.toLocaleString('ko-KR')}</p>
    {loading && <p role="status">최근 작업 조회 중…</p>}
    {errors.length>0 && <p role="status">일부 이력을 확인하지 못했습니다: {errors.join(', ')}</p>}
    {!loading && !matching.length && <p>조건에 맞는 최근 작업이 없습니다.</p>}
    <div className="session-job-list">{matching.slice(currentPage*pageSize,(currentPage+1)*pageSize).map(({source,record})=><article className="session-job" key={source.service+'/'+record.id}>
      <div className="session-job-heading"><strong>{source.service}</strong><span>{labels[record.recorded_status] || record.recorded_status}</span></div>
      <JobIdentifier id={record.id} compact/>
      {(source.result_kind || source.service==='kimodo') && <button type="button" onClick={()=>setSelected({source,id:record.id})}>상태·결과 보기</button>}
      {source.result_path && <a href={source.result_path+'?'+new URLSearchParams({job:record.id,session})}>생성기에서 열기</a>}
    </article>)}</div>
    {matching.length>0 && <QueuePagination label="전체 생성기 최근 작업 페이지" page={currentPage} size={pageSize} total={matching.length} onPage={setPage} onSize={value=>{setPageSize(value);setPage(0);}}/>}
    {selected && <section aria-label="최근 작업 결과"><button type="button" onClick={()=>setSelected(null)}>결과 닫기</button><MediaJobResult key={selected.source.service+'/'+selected.id} service={selected.source.service} id={selected.id} kind={selected.source.service==='kimodo'?'video':selected.source.result_kind} folderLink/></section>}
  </section>;
}
