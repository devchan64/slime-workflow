import React,{useEffect,useId,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {isSpriteAnchorHistoryId,restoreSpriteAnchors} from "./spriteAnchorRestore.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";


export function spriteAnchorSourceIdentity(original){
  return JSON.stringify([original.source,original.path,original.imageSha256,original.metadataSha256,original.animation.animationId,original.animation.version]);
}

export default function SpriteAnchorRestore({original,rows,onRestore}){
  const identity=spriteAnchorSourceIdentity(original);
  return <SpriteAnchorRestoreForSource key={identity} original={original} rows={rows} onRestore={onRestore}/>;
}

export function SpriteAnchorRestoreHelp(){
  return <p>현재 앵커는 별도 이력으로 저장되며 복원은 편집표에 적용됩니다. 이 저장과 복원은 원본 에셋을 변경하지 않습니다.</p>;
}

export function SpriteAnchorRestoreExpired({review,rows,noticeRef}){
  return review && review.before!==rows ? <p ref={noticeRef} tabIndex={-1} className="ui-focus-target" role="status">편집표가 변경되어 복원 검토가 만료되었습니다. 복원 내용을 다시 확인하세요.</p> : null;
}

function SpriteAnchorRestoreForSource({original,rows,onRestore}){
  const [items,setItems]=useState([]),[id,select]=useState(""),[review,setReview]=useState(null);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState(""),[failed,setFailed]=useState(false),[loaded,setLoaded]=useState(false),[saveUncertain,setSaveUncertain]=useState(false);
  const readRequest=useRef(null),writeRequest=useRef(null),saving=useRef(false),uncertainRef=useRef(false),mounted=useRef(true),uncertainHelp=useId();
  const selectedId=useRef("");
  const latestRows=useRef(rows);latestRows.current=rows;
  const focusPending=useRef(null),selectRef=useRef(null),reviewRef=useRef(null),expiredRef=useRef(null),prepareRef=useRef(null),noticeRef=useRef(null);
  useEffect(()=>{mounted.current=true;return ()=>{mounted.current=false;const current=readRequest.current;readRequest.current=null;current?.abort();writeRequest.current?.abort();};},[]);
  useEffect(()=>{if(busy || !focusPending.current)return;const pending=focusPending.current;focusPending.current=null;const target=pending.target==="select" ? selectRef.current : pending.target==="review" ? reviewRef.current || expiredRef.current : pending.target==="prepare" ? prepareRef.current : pending.target==="notice" ? noticeRef.current : pending.trigger;restoreLostFocus(document,target);},[busy,review,notice]);
  function beginFocus(event){focusPending.current=event?.currentTarget===document.activeElement ? {trigger:event.currentTarget,target:"trigger"} : null;}
  function selectId(value){selectedId.current=value;select(value);}
  async function read(operation,payload){
    const controller=readRequest.current;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{return await untilAborted(managementCommand("character-animation",operation,payload,{signal:controller.signal}),controller.signal);}
    catch(problem){if(timedOut)throw new Error("앵커 이력 조회 시간이 초과됐습니다. 다시 조회하세요.");throw problem;}
    finally{clearTimeout(timer);}
  }
  async function list(event){
    if(readRequest.current || saving.current)return;
    beginFocus(event);
    const controller=new AbortController();readRequest.current=controller;
    setBusy(true);setNotice("");setFailed(false);
    try{
      const result=await read("anchor-history",{
        animation_id:original.animation.animationId,animation_version:original.animation.version
      });
      if(!Array.isArray(result?.items) || result.items.some(item=>!item || !isSpriteAnchorHistoryId(item.id)) || new Set(result.items.map(item=>item.id)).size!==result.items.length)throw new Error("앵커 이력 목록을 확인할 수 없습니다.");
      if(readRequest.current!==controller)return;
      if(focusPending.current && result.items.length)focusPending.current.target="select";
      setItems(result.items);selectId(result.items.some(item=>item.id===selectedId.current) ? selectedId.current : result.items[0]?.id || "");setReview(null);setLoaded(true);setNotice(result.items.length+"개 이력");
    }catch(problem){if(readRequest.current===controller){setFailed(true);setNotice((problem.message || "앵커 이력을 확인할 수 없습니다.")+(loaded ? " 이전 목록을 유지합니다." : ""));}}
    finally{if(readRequest.current===controller){readRequest.current=null;setBusy(false);}}
  }
  async function save(event){
    if(readRequest.current || saving.current || uncertainRef.current)return;saving.current=true;
    beginFocus(event);
    let dispatched=false,controller=null,timer=null;
    setBusy(true);setReview(null);setNotice("");setFailed(false);
    try{
      const animation=original.animation,image=original.path.split("/").pop();
      if(rows.length!==animation.frames.length)throw new Error("원본 프레임 수와 다릅니다.");
      const frames=animation.frames.map(({frameId,rect,direction},index)=>{
        const row=rows[index];
        if(["x","y","width","height"].some(key=>row[key]==="" || Number(row[key])!==rect[key]))throw new Error("크롭 변경을 원본에 먼저 반영하세요.");
        if(!direction){
          const directions=new Set((animation.clips || []).filter(clip=>clip.frames.some(f=>f.frameId===frameId)).map(clip=>clip.direction));
          if(directions.size!==1)throw new Error("등록된 프레임 방향을 확인할 수 없습니다.");
          direction=[...directions][0];
        }
        if(row.anchorX==="" || row.anchorY==="")throw new Error("앵커 좌표를 입력하세요.");
        const anchor={x:Number(row.anchorX),y:Number(row.anchorY)};
        if(!Number.isFinite(anchor.x) || !Number.isFinite(anchor.y) || anchor.x<0 || anchor.y<0 || anchor.x>=rect.width || anchor.y>=rect.height)throw new Error((index+1)+"번 프레임의 앵커 좌표는 크롭 영역 안의 유한한 숫자여야 합니다.");
        return {frameId,rect,direction,image,anchor,points:[anchor]};
      });
      const document={schemaVersion:1,artifactType:"character-animation-anchor-review",coordinateMode:"anchor",
        description:"스프라이트 시트 편집기에서 저장한 현재 시트 앵커",frames,
        source:{animationId:animation.animationId,animationVersion:animation.version,sheets:[{image,sha256:original.imageSha256}]}};
      controller=new AbortController();writeRequest.current=controller;
      timer=setTimeout(()=>controller.abort(),30000);dispatched=true;
      const saved=await untilAborted(managementCommand("character-animation","anchor-save",{document},{signal:controller.signal}),controller.signal);
      if(!isSpriteAnchorHistoryId(saved?.id))throw new Error("저장된 앵커 이력 ID를 확인할 수 없습니다.");
      setItems(previous=>[{id:saved.id},...previous.filter(item=>item.id!==saved.id)]);
      if(focusPending.current)focusPending.current.target="select";
      selectId(saved.id);setNotice("앵커 이력 저장 완료 · "+saved.id+(latestRows.current!==rows ? " · 저장 요청 후 편집표가 변경되어 현재 값은 이 기록과 다를 수 있습니다." : ""));
    }catch(problem){if(mounted.current){setFailed(true);if(focusPending.current)focusPending.current.target="notice";if(dispatched){uncertainRef.current=true;setSaveUncertain(true);setNotice("저장 결과를 확인할 수 없습니다. 중복 저장하지 말고 이력을 확인한 뒤 편집기를 다시 여세요.");}else setNotice(problem.message || "앵커 입력을 확인할 수 없습니다.");}}
    finally{if(timer!==null)clearTimeout(timer);if(writeRequest.current===controller)writeRequest.current=null;saving.current=false;if(mounted.current)setBusy(false);}
  }
  async function prepare(event){
    const chosenId=selectedId.current;
    if(readRequest.current || saving.current || !chosenId)return;
    beginFocus(event);
    const controller=new AbortController();readRequest.current=controller;
    setBusy(true);setNotice("");setFailed(false);
    try{
      const result=await read("anchor-load",{id:chosenId});
      if(readRequest.current!==controller || selectedId.current!==chosenId)return;
      const next={...restoreSpriteAnchors(result.document,original),before:rows};
      if(readRequest.current===controller){if(focusPending.current)focusPending.current.target="review";setReview(next);}
    }catch(problem){if(readRequest.current===controller && selectedId.current===chosenId){setFailed(true);setNotice(problem.message || "복원 이력을 확인할 수 없습니다.");}}
    finally{if(readRequest.current===controller){readRequest.current=null;setBusy(false);}}
  }
  return <details><summary>앵커 이력 저장·복원</summary><fieldset disabled={busy}>
    <SpriteAnchorRestoreHelp/>
    <button type="button" disabled={saveUncertain} aria-describedby={saveUncertain ? uncertainHelp : undefined} onClick={save}>현재 앵커를 이력으로 저장</button>
    {saveUncertain && <p id={uncertainHelp}>저장 결과 확인이 필요해 다시 저장할 수 없습니다. 이력을 조회하고 편집기를 다시 여세요.</p>}
    <button type="button" onClick={list}>좌표 이력 조회</button>
    <label>좌표 이력<select ref={selectRef} value={id} onChange={e=>{selectId(e.target.value);setReview(null);}}>
      {!items.length && <option value="">{loaded ? "조회된 이력이 없습니다" : "먼저 이력을 조회하세요"}</option>}
      {items.map(item=><option key={item.id}>{item.id}</option>)}</select></label>
    <button ref={prepareRef} type="button" disabled={!id} onClick={prepare}>복원 내용 확인</button>
    <SpriteAnchorRestoreExpired review={review} rows={rows} noticeRef={expiredRef}/>
    {review?.before===rows && <section ref={reviewRef} tabIndex={-1} className="ui-focus-target" aria-label="앵커 복원 검토"><p>{id} · {review.rows.length}프레임의 크롭과 앵커를 편집표에 복원합니다.</p>
      <button type="button" onClick={event=>{beginFocus(event);if(focusPending.current)focusPending.current.target="notice";onRestore(review);setReview(null);setFailed(false);setNotice("편집표에 복원했습니다.");}}>편집표에 복원</button>
      <button type="button" onClick={event=>{beginFocus(event);if(focusPending.current)focusPending.current.target="prepare";setReview(null);}}>복원 취소</button></section>}
    {busy && <p role="status">앵커 이력을 처리하고 있습니다.</p>}
    {notice && <p ref={noticeRef} tabIndex={-1} className="ui-focus-target" role={failed ? "alert" : "status"}>{notice}</p>}
  </fieldset></details>;
}
