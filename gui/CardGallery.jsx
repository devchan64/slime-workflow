import React, {useEffect, useId, useRef, useState} from "react";
import {restoreLostFocus} from "./restoreLostFocus.mjs";
import {imageRetryUrl} from "./imageRetryUrl.mjs";
import {startVisibleImageLoadDeadline} from "./imageLoadDeadline.mjs";

function GalleryThumbnail({src,onFailure}) {
  const image=useRef(null),cancelDeadline=useRef(null),settled=useRef(false);
  useEffect(()=>{
    if(settled.current)return;
    const cancel=startVisibleImageLoadDeadline(image.current,()=>{settled.current=true;cancelDeadline.current=null;onFailure();});
    cancelDeadline.current=cancel;
    return ()=>{cancel();if(cancelDeadline.current===cancel)cancelDeadline.current=null;};
  },[]);
  function finish(failed){if(settled.current)return;settled.current=true;cancelDeadline.current?.();cancelDeadline.current=null;if(failed)onFailure();}
  return <img ref={image} width="110" loading="lazy" src={src} alt="" onLoad={()=>finish(false)} onError={()=>finish(true)}/>;
}

/** 검색·페이지 이동·선택을 제공하는 재사용 가능한 썸네일 카드 목록. */
export default function CardGallery({items, selected, onSelect, imageUrl, matches=()=>true, label="항목", pageSize=8, pageSizeOptions, placeholder="이름, 크기, 지붕 또는 입구", disabled=false, disabledReason="", revealSelection="", external=null}) {
  const [query,setQuery]=useState(""), [page,setPage]=useState(0), [failed,setFailed]=useState({});
  const [size,setSize]=useState(pageSize);
  const [imageRevisions,setImageRevisions]=useState({});
  const searchRef=useRef(null);
  const pagesRef=useRef(null), focusFrame=useRef(null),revealed=useRef("");
  useEffect(()=>()=>{if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);},[]);
  const hintId=useId();
  const disabledId=useId();
  useEffect(()=>{if(!revealSelection || revealed.current===revealSelection)return;const index=items.findIndex(item=>item.id===revealSelection);if(index>=0){revealed.current=revealSelection;setQuery("");setPage(Math.floor(index/size));}},[revealSelection,items,size]);
  const results=items.filter(item=>matches(item,query));
  const pages=Math.ceil(results.length/size);
  const current=Math.min(page,Math.max(0,pages-1));
  const visible=external ? items : results.slice(current*size,(current+1)*size);
  const selectedItem=items.find(item=>item.id===selected);
  const visibleFailures=visible.filter(item=>failed[item.id]);
  function movePage(event,delta) {
    const target=event.currentTarget,restore=document.activeElement===target;
    setPage(current+delta);
    if(!restore)return;
    if(focusFrame.current!==null)cancelAnimationFrame(focusFrame.current);
    focusFrame.current=requestAnimationFrame(()=>{
      focusFrame.current=null;
      const fallback=pagesRef.current?.querySelector('button:not(:disabled)') || searchRef.current;
      if(document.activeElement===target && target.disabled && fallback?.isConnected && !fallback.disabled)fallback.focus();
      else if(!restoreLostFocus(document,target))restoreLostFocus(document,fallback);
    });
  }
  const failures=visibleFailures.length>0 && <div><p role="status">현재 페이지의 미리보기 {visibleFailures.length}개를 불러오지 못했습니다.</p><button type="button" onClick={event=>{if(document.activeElement===event.currentTarget)(searchRef.current || external?.focusFallback?.current)?.focus();setImageRevisions(current=>{const next={...current};for(const item of visibleFailures)next[item.id]=(next[item.id] || 0)+1;return next;});setFailed(current=>{const next={...current};for(const item of visibleFailures)delete next[item.id];return next;});}}>미리보기 다시 불러오기</button></div>;
  const cards=<div className="flux-guides-list">{visible.map(item=>{const src=imageUrl(item),blocked=disabled || Boolean(external?.disabledItem?.(item));return <button type="button" key={item.id} disabled={blocked} aria-describedby={blocked ? (external?.disabledReasonId || (disabledReason ? disabledId : undefined)) : undefined} aria-pressed={selected===item.id} onClick={event=>onSelect(item.id,event)}>{failed[item.id] ? <span>미리보기 없음</span> : <GalleryThumbnail key={src+':'+(imageRevisions[item.id] || 0)} src={imageRevisions[item.id] ? imageRetryUrl(src,imageRevisions[item.id]) : src} onFailure={()=>setFailed(value=>({...value,[item.id]:true}))}/>}<span>{item.label===item.id ? item.id : `${item.label} · ${item.id}`}{item.description && <small> · {item.description}</small>}</span></button>;})}</div>;
  if(external)return <section className="card-gallery" aria-label={label+" 카드 갤러리"}>{!items.length && <p>{external.emptyMessage}</p>}{failures}{cards}</section>;
  return <section className="card-gallery" aria-label={label+" 카드 갤러리"}>
    <div className="flux-guides-toolbar"><label>{label} 검색 <input ref={searchRef} type="search" value={query} onChange={event=>{setQuery(event.target.value);setPage(0);}} placeholder={placeholder}/></label>{query && <button type="button" onClick={()=>{setQuery("");setPage(0);searchRef.current?.focus();}}>검색 초기화</button>}{pageSizeOptions && <label>페이지 크기 <select value={size} onChange={event=>{setSize(Number(event.target.value));setPage(0);}}>{pageSizeOptions.map(value=><option key={value} value={value}>{value}개</option>)}</select></label>}</div>
    <p aria-live="polite">검색 결과 {results.length}건</p>
    {selected && <p role="status">선택한 {label} · {selectedItem ? (selectedItem.label===selectedItem.id ? selectedItem.id : `${selectedItem.label} · ${selectedItem.id}`) : selected}{!visible.some(item=>item.id===selected) && " · 현재 페이지에 표시되지 않습니다."}</p>}
    {disabled && disabledReason && <p id={disabledId}>{disabledReason}</p>}
    {!results.length && <p>일치하는 항목이 없습니다. 검색어를 바꿔 보세요.</p>}
    {failures}{cards}
    <nav ref={pagesRef} className="flux-guides-pages" aria-label={label+" 페이지 이동"}><button type="button" disabled={current===0} aria-describedby={current===0 ? hintId : undefined} onClick={event=>movePage(event,-1)}>이전</button><span aria-live="polite">{pages ? current+1 : 0} / {pages} 페이지</span><button type="button" disabled={current+1>=pages} aria-describedby={current+1>=pages ? hintId : undefined} onClick={event=>movePage(event,1)}>다음</button><small id={hintId}>{!pages ? "검색 결과가 없습니다." : pages===1 ? "표시할 다른 페이지가 없습니다." : current===0 ? "첫 페이지입니다." : current+1===pages ? "마지막 페이지입니다." : ""}</small></nav>
  </section>;
}
