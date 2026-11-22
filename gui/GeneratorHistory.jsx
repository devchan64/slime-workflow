import JobStatus from "./JobStatus.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import React, {useEffect,useId,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import SelectedHistoryDeletion from "./SelectedHistoryDeletion.jsx";
import {requestErrorMessage} from "./requestError.mjs";
import {historyInputSummary} from "./historyInputSummary.mjs";

function recordedTime(id) {
  const match=typeof id==="string" && id.match(/^(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})-/);
  return match ? `ID 시각 · ${match[1]} ${match[2]}:${match[3]}:${match[4]} (한국 시간)` : "";
}
const fluxServices=new Set(["flux-image","flux-character","flux-mannequin","flux-billboard","flux-prop","flux-vegetation","flux-building","flux-seamless","flux-expression"]);
const videoServices=new Set(["wan22-fun-control","wan22-vace","wan22-animate2","dwpose","kimodo"]);
function HistoryImage({service,record,summary,unavailable}) {

  const flux=fluxServices.has(service), video=videoServices.has(service);
  if(!flux && !video)return null;
  if(!summary)return <span className="history-card-image-placeholder">{unavailable ? "이미지 확인 불가" : "이미지 확인 중"}</span>;
  const attempt=typeof summary.image_attempt==="string" && /^[a-f0-9]{32}$/.test(summary.image_attempt) ? summary.image_attempt : "";
  if((flux && !summary.image_available) || (video && !attempt))return <span className="history-card-image-placeholder">{["queued","running"].includes(record.recorded_status) ? "결과 준비 중" : "이미지 없음"}</span>;
  const src=flux ? `/${service}-generator/jobs/${encodeURIComponent(record.id)}/result.png` : `/${service}/jobs/${encodeURIComponent(record.id)}/attempts/${attempt}/output-000.png`;
  return <HistoryThumbnail key={src} src={src}/>;
}

function HistoryThumbnail({src}) {
  const [failed,setFailed]=useState(false);
  if(failed)return <span className="history-card-image-placeholder">이미지 확인 불가</span>;
  return <img className="history-card-image" loading="lazy" decoding="async" src={src} alt="생성 결과 미리보기" onError={()=>setFailed(true)}/>;
}

export default function GeneratorHistory({service, statusCommand, restore, inspectResult, openResult, renderResult, readJob, allowPriority=false, onSelectedDeleted, card=false, resultId='', externalResultId='', onCloseResult, footer}) {
  const resultPanelId=useId(),searchHelpId=useId(),searchErrorId=useId();
  const detailsRef=useRef(null),selectedRef=useRef(null);
  const [expanded,setExpanded]=useState(null);
  const [page,setPage]=useState(null);
  const [query,setQuery]=useState("");
  const searchRef=useRef(null);
  const [filter,setFilter]=useState("");
  const [pageSize,setPageSize]=useState(10);
  const [selected,setSelected]=useState(null);
  const [job,setJob]=useState(null);
  const [busy,setBusy]=useState(false);
  const pending=useRef(false);
  const [error,setError]=useState("");
  const [summaries,setSummaries]=useState({});
  const [summaryNotice,setSummaryNotice]=useState("");
  const [resultLookup,setResultLookup]=useState(null);
  const [lookupRevision,retryLookup]=useState(0);
  useEffect(()=>{
    if(!resultId)return;
    if(detailsRef.current)detailsRef.current.open=true;
    const visible=page?.records.find(record=>record.id===resultId);
    if(visible){setSelected(visible);setResultLookup({id:resultId});return;}
    let active=true;
    setResultLookup({id:resultId,loading:true});
    (async()=>{
      try{
        let result;
        for(let attempt=0;attempt<3;attempt++){
          try{result=await managementCommand(service,'history-observe',{limit:30,offset:0,query:resultId});break;}
          catch(problem){if(attempt===2 || !requestErrorMessage(problem).includes('이력 조회가 이미 진행 중'))throw problem;await new Promise(resolve=>setTimeout(resolve,1000));if(!active)return;}
        }
        if(!Array.isArray(result.records))throw new Error('이력 응답을 확인할 수 없습니다.');
        if(!active)return;
        const match=result.records.find(record=>record.id===resultId);
        if(!match){setResultLookup({id:resultId,error:'이력에서 해당 작업을 찾지 못했습니다. 작업 결과를 직접 확인합니다.'});return;}
        setPage(result);setQuery(resultId);setFilter(resultId);setSelected(match);setJob(null);setResultLookup({id:resultId});
      }catch(problem){if(active)setResultLookup({id:resultId,error:'이력 조회 실패 · '+requestErrorMessage(problem)+' · 작업 결과를 직접 확인합니다.'});}
    })();
    return ()=>{active=false;};
  },[resultId,service,lookupRevision]);
  useEffect(()=>{
    setSummaries({});setSummaryNotice("");
    if(!page?.records.length)return;
    const controller=new AbortController();
    const ids=page.records.map(record=>record.id).filter(id=>/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(id));
    if(!ids.length)return ()=>controller.abort();
    fetch("/management/history-summaries",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({service,ids}),signal:controller.signal})
      .then(response=>{if(!response.ok)throw new Error();return response.json();})
      .then(result=>{if(!result.summaries || typeof result.summaries!=="object" || Array.isArray(result.summaries))throw new Error();if(!controller.signal.aborted){setSummaries(result.summaries);if(ids.some(id=>!Object.hasOwn(result.summaries,id)))setSummaryNotice("일부 저장 입력 요약을 확인할 수 없습니다. 작업을 선택해 입력을 확인하세요.");}})
      .catch(()=>{if(!controller.signal.aborted)setSummaryNotice("저장 입력 요약을 불러오지 못했습니다. 이력을 새로고침하거나 작업을 선택해 입력을 확인하세요.");});
    return ()=>controller.abort();
  },[page,service]);
  async function perform(operation) {
    if(pending.current)return;
    const focused=detailsRef.current?.contains(document.activeElement) ? document.activeElement : null;
    pending.current=true;setBusy(true); setError("");
    try { await operation(); }
    catch(problem) { setError(requestErrorMessage(problem)); }
    finally {
      pending.current=false;setBusy(false);
      requestAnimationFrame(()=>{
        if(!focused?.isConnected || document.activeElement!==document.body)return;
        if(!focused.disabled)focused.focus();
        else if(focused.closest('.generator-history-pagination'))
          (detailsRef.current?.querySelector('.generator-history-pagination button:not(:disabled)') || searchRef.current)?.focus();
      });
    }
  }
  async function list(offset, search, size=pageSize) {
    if(search && !/^[A-Za-z0-9_-]+$/.test(search))throw new Error("작업 ID 검색에는 영문, 숫자, 하이픈(-), 밑줄(_)만 사용할 수 있습니다.");
    const payload={limit:size,offset,query:search};
    if(offset)payload.snapshot=page.snapshot;
    try {
      const result=await managementCommand(service,"history-observe",payload);
      if(!Array.isArray(result.records))throw new Error("이력 응답을 확인할 수 없습니다.");
      const ids=new Set(result.records.map(record=>record.id));
      setSelected(current=>{
        if(current && ids.has(current.id))return result.records.find(record=>record.id===current.id);
        return result.records.find(record=>record.id===(resultId || externalResultId || expanded)) || null;
      });
      setJob(current=>current && ids.has(current.id) ? current : null);
      setPage(result);setFilter(search);setPageSize(size);
    } catch(problem) {
      throw new Error(requestErrorMessage(problem)+(page ? " · 이전 이력과 선택을 유지합니다." : "")+" 다시 조회하세요.");
    }
  }
  function deleted(id,message) {
    setExpanded(null);setSelected(null);
    setJob(null);
    setPage(previous=>({...previous,records:previous.records.filter(record=>record.id!==id),total:Math.max(0,previous.total-1)}));
    onSelectedDeleted(id,message);
    perform(()=>list(0,filter));
  }
  async function read(id) {
    const result=readJob ? await readJob(id) : await managementCommand(service,statusCommand,{id});
    if(result.id!==id || !result.request)throw new Error("작업 입력을 확인할 수 없습니다.");
    return result;
  }
  async function showResult(id) {
    if(openResult) openResult(id);
    else if(inspectResult) inspectResult(await read(id));
  }
  async function showInput(id) {
    const result=await read(id);
    setJob(result);
  }
  return <details ref={detailsRef} className={`generator-history${card ? ' generator-section-card' : ''}`} onToggle={event=>{
    if(event.currentTarget.open && !page && !error && !resultId)perform(()=>list(0,query.trim()));}}><summary>{card ? <span className="generator-section-card-heading" role="heading" aria-level="2">생성 이력</span> : '생성 이력'}</summary>
    <fieldset className={card ? 'generator-section-card-body' : undefined} disabled={busy}><div className="generator-history-toolbar">
      <label>작업 ID 검색 <input ref={searchRef} value={query} maxLength={80} aria-describedby={error.startsWith("작업 ID 검색에는 영문") ? `${searchHelpId} ${searchErrorId}` : searchHelpId} aria-invalid={error.startsWith("작업 ID 검색에는 영문") || undefined} onChange={e=>{setQuery(e.target.value);setError(value=>value.startsWith("작업 ID 검색에는 영문") ? "" : value);}} onKeyDown={e=>{if(e.key==="Enter" && !e.nativeEvent.isComposing){e.preventDefault();perform(()=>list(0,query.trim()));}}}/><small id={searchHelpId}>ID의 일부를 검색할 수 있습니다. 영문, 숫자, 하이픈(-), 밑줄(_)을 사용하세요.</small></label>
      <label>페이지당 이력 <select value={pageSize} onChange={e=>{const size=Number(e.target.value);perform(()=>list(0,query.trim(),size));}}>{[5,10,20,30].map(size=><option key={size} value={size}>{size}건</option>)}</select></label>
      <button type="button" onClick={()=>perform(()=>list(0,query.trim()))}>{busy?"조회 중…":page && query.trim()===filter?"이력 새로고침":"이력 조회"}</button>
      {(query || filter) && <button type="button" onClick={()=>{setQuery("");perform(()=>list(0,"")).then(()=>requestAnimationFrame(()=>{if(document.activeElement===document.body)searchRef.current?.focus();}));}}>검색 초기화</button>}
    </div>
      {resultId && resultLookup?.id===resultId && resultLookup.loading && <p role="status">선택한 작업을 이력에서 찾고 있습니다.</p>}
      {resultId && resultLookup?.id===resultId && resultLookup.error && <section className="history-action-detail" aria-label="이력 밖 선택 결과"><p role="alert">{resultLookup.error}</p><button type="button" onClick={()=>retryLookup(value=>value+1)}>이력에서 다시 찾기</button>{renderResult?.(resultId,()=>{onCloseResult?.();requestAnimationFrame(()=>detailsRef.current?.querySelector('summary')?.focus());})}</section>}
      {resultId && resultLookup?.id===resultId && !resultLookup.loading && !resultLookup.error && page && !page.records.some(record=>record.id===resultId) && <section className="history-action-detail" aria-label="이력 범위 밖 선택 결과"><p>선택한 작업이 현재 이력 검색 또는 페이지 범위 밖에 있습니다.</p>{renderResult?.(resultId,()=>{onCloseResult?.();requestAnimationFrame(()=>detailsRef.current?.querySelector('summary')?.focus());})}</section>}
      {!openResult && expanded && page && !page.records.some(record=>record.id===expanded) && <section className="history-action-detail" aria-label="이력 범위 밖 선택 결과"><p>선택한 작업이 현재 이력 검색 또는 페이지 범위 밖에 있습니다.</p><button type="button" onClick={()=>{setExpanded(null);requestAnimationFrame(()=>searchRef.current?.focus());}}>결과 닫기</button>{renderResult?.(expanded)}</section>}
      {page && <>
        {query.trim()!==filter && <p role="status">검색어가 변경되었습니다. 아래는 이전 조회 결과입니다. 이력 조회를 눌러 적용하세요.</p>}
        {externalResultId && !page.records.some(record=>record.id===externalResultId) && <p role="status">열린 작업 결과는 현재 이력 검색 또는 페이지 범위 밖에 있습니다.</p>}
        {externalResultId && selected && selected.id!==externalResultId && <p role="status">아래 열린 결과는 현재 선택한 이력과 다른 작업입니다.</p>}
        <p role="status">총 {page.total}건 · 이번 조회 {page.records.length}건</p>
        {summaryNotice && <p role="status">{summaryNotice}</p>}
        {page.records.length===0 && <p>조회된 이력이 없습니다. 검색 조건을 바꾸거나 새 작업을 생성하세요.</p>}
        <div className="generator-history-list">{page.records.map(record=><div className="generator-history-item" data-history-id={record.id} key={record.id}>
          <button type="button" ref={selected?.id===record.id ? selectedRef : undefined} className="generator-history-select" aria-pressed={selected?.id===record.id} onClick={()=>{if(selected?.id!==record.id){setExpanded(null);if(resultId)onCloseResult?.();}setSelected(record);setJob(null);setError(value=>value.startsWith("작업 ID 검색에는 영문") ? value : "");}}>
            <HistoryImage key={record.id} service={service} record={record} summary={summaries[record.id]} unavailable={Boolean(summaryNotice)}/><span className="history-card-content"><span className="history-card-heading"><JobStatus state={record.recorded_status}/>{recordedTime(record.id) && <span>{recordedTime(record.id)}</span>}</span>{historyInputSummary(summaries[record.id]).length>0 && <span className="history-card-summary">{historyInputSummary(summaries[record.id]).join(" · ")}</span>}</span>
          </button>
          <JobIdentifier id={record.id} compact/>
          {selected?.id===record.id && <section className="generator-history-selection" aria-label={"선택 이력 · "+record.id}>
            <div className="generator-history-actions">
              {renderResult && !openResult && <button type="button" className="history-action-result" aria-expanded={expanded===record.id}
                aria-controls={resultPanelId} onClick={()=>setExpanded(current=>current===record.id ? null : record.id)}>
                {expanded===record.id ? "결과 접기" : "결과 펼치기"}</button>}
              {(openResult || inspectResult) && resultId!==record.id && <button className="history-action-result" type="button" onClick={()=>openResult ? openResult(record.id) : perform(()=>showResult(record.id))}>결과 조회</button>}
              {restore && <button className="history-action-input" type="button" onClick={()=>perform(()=>showInput(record.id))}>입력값 불러오기</button>}
            </div>
            {renderResult && <div id={resultPanelId} hidden={openResult ? resultId!==record.id : expanded!==record.id} className="history-action-detail history-inline-result">{(openResult ? resultId===record.id && resultLookup?.id===resultId && !resultLookup.loading && !resultLookup.error : expanded===record.id) && renderResult(record.id,()=>{onCloseResult?.();requestAnimationFrame(()=>selectedRef.current?.focus());})}</div>}
            {onSelectedDeleted && <SelectedHistoryDeletion key={service+"/"+record.id} service={service} id={record.id} allowPriority={allowPriority} onDeleted={deleted}/>}
            {job?.id===record.id && <section className="history-action-detail">{historyInputSummary(job.request).length>0 && <p>저장 입력 · {historyInputSummary(job.request).join(" · ")}</p>}<details><summary>저장된 입력 상세</summary><pre>{JSON.stringify(job.request,null,2)}</pre></details>
              {restore && <button type="button" onClick={()=>restore(job.request,job)}>확인한 입력 적용</button>}
            </section>}
          </section>}
        </div>)}</div>
        <nav className="generator-history-pagination" aria-label="생성 이력 페이지">
          <button type="button" disabled={query.trim()!==filter || !page.offset} onClick={()=>perform(()=>list(Math.max(0,page.offset-pageSize),filter))}>이전 이력 페이지</button>
          <span aria-live="polite">{page.records.length ? `${page.offset+1}–${page.offset+page.records.length}` : "0"} / {page.total}건</span>
          <button type="button" disabled={query.trim()!==filter || page.next_offset==null} onClick={()=>perform(()=>list(page.next_offset,filter))}>다음 이력 페이지</button>
        </nav>
      </>}
    </fieldset>
    {footer && <div className="generator-section-card-body">{footer}</div>}{error && <p id={searchErrorId} role="alert">{error}</p>}
  </details>;
}
