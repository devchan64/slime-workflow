import SnapshotStatus from "./SnapshotStatus.jsx";
import BillboardLifecycle from "./BillboardLifecycle.jsx";
import BillboardRegistration from "./BillboardRegistration.jsx";
import BillboardProperties from "./BillboardProperties.jsx";
import RecoverableImage from "./RecoverableImage.jsx";
import React,{useEffect,useId,useRef,useState} from "react";
import ConversationLink from "./ConversationLink.jsx";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import ResultTable from "./ResultTable.jsx";
import CardGallery from "./CardGallery.jsx";
import {validBillboardCatalogPage,billboardCategoryLabel} from "./billboardCatalogPage.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";

const categories={vegetation:"식생",herbaceous:"초본","large-trees":"대형 나무","rocks-minerals":"바위·광물",props:"소품"};

function imageUrl(id){
  return "/management/map-assets/billboards/"+encodeURIComponent(id)+".png";
}

export default function BillboardCatalog({choose}){
  useEffect(()=>{if(!choose)document.title="공용 빌보드 에셋 관리";},[choose]);
  const [query,setQuery]=useState(""),[category,setCategory]=useState("");
  const [request,setRequest]=useState({offset:0,limit:10}),[page,setPage]=useState(null);
  const [notice,setNotice]=useState(""),[uncertainNotices,setUncertainNotices]=useState([]);
  const [loading,setLoading]=useState(true),[displayedRequest,setDisplayedRequest]=useState(null);
  const [imageRevision,setImageRevision]=useState(0),[editingProperties,setEditingProperties]=useState(false);
  const [lifecycleActive,setLifecycleActive]=useState(false);
  const [selected,select]=useState(null),[error,setError]=useState("");
  const detailRef=useRef(null),triggerRef=useRef(null),searchRef=useRef(null),resultsRef=useRef(null),errorRef=useRef(null),restoreSearchFocus=useRef(false),focusEpoch=useRef(0);
  const editingReasonId=useId(),lifecycleReasonId=useId(),loadingId=useId(),pageReasonId=useId();
  const locked=editingProperties || lifecycleActive;
  const lockDescription=[editingProperties && editingReasonId,lifecycleActive && lifecycleReasonId].filter(Boolean).join(" ") || undefined;
  useEffect(()=>()=>{focusEpoch.current++;},[]);
  useEffect(()=>{if(selected && triggerRef.current && (document.activeElement===triggerRef.current || document.activeElement===document.body))detailRef.current?.focus();},[selected]);
  useEffect(()=>{
    if(loading || !restoreSearchFocus.current)return;
    restoreSearchFocus.current=false;
    restoreLostFocus(document,(error ? errorRef : resultsRef).current);
  },[loading,error,page]);
  useEffect(()=>{
    let active=true,timedOut=false;
    const controller=new AbortController(),timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setLoading(true);setError("");
    untilAborted(managementCommand("hermes-agent","hermes-billboard-catalog",request,{signal:controller.signal}),controller.signal).then(result=>{
      if(!validBillboardCatalogPage(result,request))throw new Error("빌보드 목록 응답 형식을 확인할 수 없습니다.");
      if(active){setPage(result);setDisplayedRequest(request);setLoading(false);}
    }).catch(problem=>{if(active){setError(timedOut ? "카탈로그 조회 시간이 초과됐습니다. 다시 검색하세요." : requestErrorMessage(problem));setLoading(false);}}).finally(()=>clearTimeout(timeout));
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[request]);
  function search(e){
    e.preventDefault();
    if(loading || locked)return;
    restoreSearchFocus.current=document.activeElement===searchRef.current;
    setRequest({offset:0,limit:10,query,...(category?{category}:{})});
  }
  function movePage(offset,event){restoreSearchFocus.current=document.activeElement===event.currentTarget;setRequest({...request,offset});}
  function closeDetail(){
    const epoch=++focusEpoch.current,target=triggerRef.current;
    select(null);
    requestAnimationFrame(()=>{if(epoch!==focusEpoch.current)return;if(!restoreLostFocus(document,target))restoreLostFocus(document,searchRef.current);});
  }
  const resultsStale=!!page && displayedRequest!==request;
  const filtersChanged=query!==(request.query || "") || category!==(request.category || "");
  const pageReason=loading ? "조회가 끝나면 페이지를 이동할 수 있습니다." : resultsStale ? "목록을 다시 검색한 뒤 페이지를 이동하세요." : filtersChanged ? "변경된 검색 조건으로 검색한 뒤 페이지를 이동하세요." : "";
  const emptyResults=loading || resultsStale || filtersChanged ? "이전 조회에서 표시할 빌보드가 없었습니다." : page?.total ? "현재 페이지에 표시할 빌보드가 없습니다. 이전 페이지를 확인하세요." : "조회한 조건에 맞는 빌보드가 없습니다.";
  function selectAsset(id,event){
    const asset=page.items.find(item=>item.id===id);
    if(!asset)return;
    focusEpoch.current++;triggerRef.current=event.currentTarget;
    if(selected?.id===id)detailRef.current?.focus();else select(asset);
  }
  const DetailHeading=choose ? "h3" : "h2";
  return <section className={"billboard-catalog"+(!choose ? " billboard-standalone" : "")}>{!choose && <ConversationLink/>}{choose ? <h2>공용 빌보드 에셋</h2> : <h1>공용 빌보드 에셋</h1>}
    <fieldset disabled={locked} style={{border:0,padding:0,margin:0}}><BillboardRegistration onSaved={()=>setRequest({...request,offset:0})}/></fieldset>
    {editingProperties && <p id={editingReasonId} role="status">공용 속성 편집 중입니다. 다른 에셋을 열거나 검색하려면 편집을 취소하거나 저장하세요.</p>}
    {lifecycleActive && <p id={lifecycleReasonId} role="status">원본 축소 또는 폐기를 검토 중입니다. 다른 에셋을 열거나 검색하려면 검토를 취소하거나 완료하세요.</p>}
    <form className="billboard-search" onSubmit={search}><label>분류<select value={category} onChange={e=>setCategory(e.target.value)}>
      <option value="">전체</option>{Object.entries(categories).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
      <label>이름·ID·모델링 설명·사용 맵<input maxLength={100} value={query} onChange={e=>setQuery(e.target.value)}/></label>
      <button ref={searchRef} disabled={loading || locked} aria-describedby={[lockDescription,loading && loadingId].filter(Boolean).join(" ") || undefined}>{loading?"조회 중…":"빌보드 검색"}</button></form>
    {filtersChanged && page && !loading && <p role="status">검색 조건이 변경되었습니다. {page.items.length ? "아래는 이전 조건의 결과입니다." : "이전 조회에 표시할 빌보드가 없었습니다."} 빌보드 검색을 눌러 적용하세요.</p>}
    {loading && <p id={loadingId} role="status">{page ? (page.items.length ? "새 결과를 조회하고 있습니다. 아래는 이전 조회 결과입니다." : "새 결과를 조회하고 있습니다. 이전 조회에 표시할 빌보드가 없었습니다.") : "카탈로그 조회 중…"}</p>}
    {resultsStale && !loading && <p role="status">조회에 실패했습니다. {page.items.length ? "아래는 이전 조회 결과입니다." : "이전 조회에 표시할 빌보드가 없었습니다."}</p>}
    {page?.storage==="database" && <SnapshotStatus/>}
    {notice && <p role="status">{notice}</p>}
    {uncertainNotices.map(warning=><div key={warning.texture+"/"+warning.requestId}><p role="alert">{warning.texture} · {warning.message}</p><button type="button" aria-label={"확인 안내 닫기 · "+warning.texture+" · 접수 "+warning.requestId} onClick={event=>{const focused=document.activeElement===event.currentTarget;setUncertainNotices(previous=>previous.filter(item=>item!==warning));if(focused)requestAnimationFrame(()=>restoreLostFocus(document,searchRef.current?.disabled ? detailRef.current : searchRef.current));}}>확인 안내 닫기</button></div>)}
    {error && <p ref={errorRef} tabIndex={-1} role="alert">{error}</p>}
    {page && pageReason && (page.offset>0 || page.next_offset!=null) && <p id={pageReasonId}>{pageReason}</p>}
    {page && <><div ref={resultsRef} tabIndex={-1} aria-label="빌보드 검색 결과"><h2>검색 결과</h2><p aria-live="polite">{page.total}종{page.items.length ? " · "+(page.offset+1)+"–"+(page.offset+page.items.length)+"번째" : ""}</p>
      <CardGallery label="빌보드" items={page.items.map(asset=>({id:asset.id,label:asset.name,description:billboardCategoryLabel(categories,asset.category)}))} selected={selected?.id} imageUrl={item=>imageUrl(item.id)+"?r="+imageRevision} onSelect={selectAsset} external={{emptyMessage:emptyResults,disabledItem:item=>loading || (locked && selected?.id!==item.id),disabledReasonId:[locked && lockDescription,loading && loadingId].filter(Boolean).join(" ") || undefined,focusFallback:searchRef}}/>
    </div>
      {page.offset>0 && <button type="button" disabled={filtersChanged || resultsStale || loading || locked} aria-describedby={[lockDescription,pageReason && pageReasonId].filter(Boolean).join(" ") || undefined} onClick={event=>movePage(Math.max(0,page.offset-page.limit),event)}>이전 페이지</button>}
      {page.next_offset!=null && <button type="button" disabled={filtersChanged || resultsStale || loading || locked} aria-describedby={[lockDescription,pageReason && pageReasonId].filter(Boolean).join(" ") || undefined} onClick={event=>movePage(page.next_offset,event)}>다음 페이지</button>}</>}
    {selected && <section ref={detailRef} tabIndex={-1} aria-label="선택한 빌보드 상세"><button type="button" disabled={locked} aria-describedby={lockDescription} onClick={closeDetail}>상세 닫기</button><DetailHeading>{selected.name}</DetailHeading>
      {page && !page.items.some(item=>item.id===selected.id) && <p role="status">열린 빌보드는 현재 검색 결과에 없습니다. 마지막으로 선택한 상세를 유지합니다.</p>}
      <RecoverableImage key={selected.id+":"+imageRevision} src={imageUrl(selected.id)+"?r="+imageRevision} name={selected.name}/>
      <p>{selected.modeling.purpose}</p><p>{selected.modeling.composition}</p>
      <div className="billboard-usage-table"><ResultTable table={{title:"사용 맵",emptyMessage:selected.maps_truncated ? "표시할 사용 맵 정보가 없습니다. 다시 검색하세요." : "이 빌보드가 배치된 맵이 없습니다.",summary:selected.maps_truncated?"처음 20개 맵":selected.maps.length+"개 맵",
        columns:["맵","원본 경로","사용 횟수"],rows:selected.maps.map(map=>[map.map,map.source_path,map.occurrences ?? "미확인"])}}/></div>
      <fieldset disabled={lifecycleActive} style={{border:0,padding:0,margin:0}}><BillboardProperties key={selected.id} texture={selected.id} onDirtyChange={setEditingProperties} onSaveUncertain={warning=>setUncertainNotices(previous=>previous.some(item=>item.texture===warning.texture && item.requestId===warning.requestId) ? previous : [...previous,warning])} onCrop={()=>setImageRevision(n=>n+1)}/></fieldset>
      <fieldset disabled={editingProperties} style={{border:0,padding:0,margin:0}}><BillboardLifecycle key={selected.id} texture={selected.id} onInteractionChange={setLifecycleActive} onComplete={(msg,{retired})=>{setNotice(msg);if(retired){restoreSearchFocus.current=document.activeElement===document.body || Boolean(detailRef.current?.contains(document.activeElement));select(null);}setImageRevision(n=>n+1);setRequest({...request,offset:0});}}/></fieldset>
      {choose && <button onClick={()=>choose("빌보드 "+selected.name,selected.id)}>대화 입력에 추가</button>}
    </section>}
  </section>;
}
