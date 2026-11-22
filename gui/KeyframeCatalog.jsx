import React,{useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

function Preview({id}){
  const [result,setResult]=useState(null),[error,setError]=useState(""),[attempt,setAttempt]=useState(0);
  useEffect(()=>{
    let active=true;
    setError("");setResult(null);
    managementCommand("hermes-agent","hermes-kimodo-keyframe-preview",{keyframe_id:id}).then(value=>{
      if(value.id!==id || !value.image_base64)throw new Error("선택한 키프레임을 확인할 수 없습니다.");
      if(active)setResult(value);
    }).catch(problem=>{if(active)setError(problem instanceof TypeError?"원본에 연결하지 못했습니다. 다시 시도하세요.":problem.message);});
    return ()=>{active=false;};
  },[id,attempt]);
  if(error)return <div role="alert"><p>{error}</p><button type="button" onClick={()=>setAttempt(value=>value+1)}>원본 다시 불러오기</button></div>;
  if(!result)return <p role="status">원본 확인 중…</p>;
  return <figure><img src={"data:image/png;base64,"+result.image_base64} alt={id+" 키프레임"} style={{maxWidth:"100%"}}/>
    <figcaption>{id} · PNG SHA-256 <code>{result.sha256}</code></figcaption></figure>;
}

function SearchResults({query,choose,add,disabled}){
  const [cursor,setCursor]=useState({}),[page,setPage]=useState(null);
  const [error,setError]=useState(""),[selected,select]=useState("");
  const [loading,setLoading]=useState(true),[receivedAt,setReceivedAt]=useState(null);
  const previewRef=useRef(null),triggerRef=useRef(null);
  useEffect(()=>{if(selected && triggerRef.current){previewRef.current?.focus({preventScroll:true});previewRef.current?.scrollIntoView({block:"start",inline:"nearest"});}},[selected]);
  function closePreview(){select("");requestAnimationFrame(()=>{if(triggerRef.current?.isConnected)triggerRef.current.focus();});}
  useEffect(()=>{
    let active=true;
    setLoading(true);setError("");
    const timer=setTimeout(()=>{
      managementCommand("hermes-agent","hermes-kimodo-keyframes",{query,limit:20,...cursor})
        .then(result=>{
          if(!result || !Array.isArray(result.items) || !Number.isInteger(result.total))throw new Error("키프레임 목록을 확인할 수 없습니다.");
          if(active){setPage(result);setReceivedAt(new Date());select("");setLoading(false);}
        })
        .catch(problem=>{if(active){setError(problem instanceof TypeError?"키프레임 목록에 연결하지 못했습니다.":problem.message);setLoading(false);}});
    },200);
    return ()=>{active=false;clearTimeout(timer);};
  },[query,cursor]);
  return <section aria-label="Kimodo 키프레임 검색">
    {error && <p role="alert">{error}{page && " 이전 조회 결과를 유지합니다."} <button type="button" onClick={()=>setCursor({})}>처음부터 다시 조회</button></p>}
    {loading && page && <p role="status">새 목록 조회 중 · 아래는 이전 결과입니다.</p>}
    {!error && !page && <p role="status">키프레임 조회 중…</p>}
    {page && <><p>화면 수신 시각 · {receivedAt?.toLocaleString("ko-KR")}</p><h3>등록 키프레임</h3><p>검색 결과 {page.total}개</p>
      {page.items.length===0 && <p>검색 조건에 맞는 키프레임이 없습니다.</p>}
      <ul className="keyframe-catalog-list">{page.items.map(row=><li key={row.id}>
        <strong>{row.tag || "키프레임"}</strong><p>원본 프레임 · {row.source_frame}</p>
        <p className="keyframe-id">ID · <code>{row.id}</code></p>
        <div className="keyframe-actions"><button type="button" aria-expanded={selected===row.id} aria-label={row.id+(selected===row.id?" 미리보기 닫기":" 미리보기 열기")} onClick={event=>{triggerRef.current=event.currentTarget;if(selected===row.id)closePreview();else select(row.id);}}>{selected===row.id?"미리보기 닫기":"미리보기"}</button>{choose && <button type="button" onClick={()=>choose("Kimodo 키프레임",row.id)}>입력에 추가</button>}
          <button type="button" disabled={disabled} onClick={()=>add(row.id,row.tag)}>배치에 추가</button></div>
      </li>)}</ul>
      {page.note && <p>{page.note}</p>}
      {cursor.offset>0 && <button disabled={loading || !!error} onClick={()=>setCursor({offset:Math.max(0,cursor.offset-20),snapshot:page.snapshot})}>이전 키프레임</button>}
      {page.next_offset!=null && <button disabled={loading || !!error} onClick={()=>setCursor({offset:page.next_offset,snapshot:page.snapshot})}>다음 키프레임</button>}
      {selected && <section ref={previewRef} tabIndex={-1} aria-label="선택한 키프레임 미리보기"><button type="button" onClick={closePreview}>미리보기 닫기</button><Preview key={selected} id={selected}/></section>}</>}
  </section>;
}

export default function KeyframeCatalog({query,choose,apply,initialFrames="",initialRows=[]}){
  const [rows,setRows]=useState(initialRows),[frames,setFrames]=useState(initialFrames);
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[review,setReview]=useState(null);
  const placementRef=useRef(null),focusPlacement=useRef(false);
  useEffect(()=>{if(rows.length && focusPlacement.current){focusPlacement.current=false;placementRef.current?.focus({preventScroll:true});placementRef.current?.scrollIntoView({block:"start",inline:"nearest"});}},[rows]);
  function edit(next){
    setRows(next);setReview(null);setError("");
  }
  async function validate(event){
    event.preventDefault();setBusy(true);setError("");setReview(null);
    try{
      const result=await managementCommand("hermes-agent","hermes-kimodo-keyframe-validate",{
        frames:Number(frames),keyframes:rows.map(row=>({id:row.id,frame:Number(row.frame)}))
      });
      if(!Array.isArray(result.placements) || result.placements.length!==rows.length || !result.skeleton_signature_sha256){
        throw new Error("배치 검증 결과를 확인할 수 없습니다.");
      }
      setReview(result);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <>
    <SearchResults key={query} query={query} choose={choose} disabled={busy || rows.length>=20}
      add={(id,tag)=>{focusPlacement.current=true;edit([...rows,{id,tag,frame:""}]);}}/>
    {apply && <button type="button" disabled={busy || rows.length>0} onClick={()=>{
      const standingPose="b0000000000000000000000000000004";
      edit([{id:standingPose,frame:1},{id:standingPose,frame:frames}]);
    }}>첫 프레임과 마지막 프레임에 기본 서기 자세 배치</button>}
    {rows.length>0 && <form ref={placementRef} tabIndex={-1} aria-label="출력 프레임 배치" onSubmit={validate}><fieldset disabled={busy}><legend>출력 프레임 배치</legend>
      <label>총 출력 프레임 수 (30~300)<input type="number" required min="30" max="300" value={frames}
        onChange={e=>{setFrames(e.target.value);setReview(null);setError("");}}/></label>
      {rows.map((row,index)=><div key={index} className="keyframe-placement-row"><strong>{row.tag || "키프레임"}</strong><p>ID · <code>{row.id}</code></p><label>출력 프레임
        <input type="number" required min="1" max={frames || undefined} value={row.frame}
          onChange={e=>edit(rows.map((item,i)=>i===index?{...item,frame:e.target.value}:item))}/></label>
        <button type="button" aria-label={(row.tag || row.id)+" 배치 삭제"} onClick={()=>edit(rows.filter((_,i)=>i!==index))}>삭제</button></div>)}
      <button>원본과 배치 검증</button>
      {error && <p role="alert">{error}</p>}
      {review && <><p role="status">{review.placements.length}개 배치 검증 완료 · {review.note}</p>
        <ResultTable table={{title:"검증된 키프레임 배치",columns:["출력 프레임","키프레임 ID"],
          rows:review.placements.map(row=>[row.frame,row.id])}}/>
        <button type="button" onClick={()=>apply ? apply(Number(frames),review) :
          choose("Kimodo 키프레임 배치",JSON.stringify({frames:Number(frames),keyframes:review.placements}))}>
          {apply?"생성 폼에 배치 적용":"검증한 배치를 대화 입력에 추가"}</button></>}
    </fieldset></form>}
  </>;
}
