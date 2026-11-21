import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";

function restore(document,original){
  const {animation,imageSha256}=original;
  if(document.source.animationId!==animation.animationId || document.source.animationVersion!==animation.version ||
    !["anchor","foot-centers","endpoints"].includes(document.coordinateMode))throw new Error("애니메이션 또는 좌표 모드가 일치하지 않습니다.");
  const images=new Set(document.source.sheets.filter(sheet=>sheet.sha256===imageSha256).map(sheet=>sheet.image));
  const frames=document.frames.filter(frame=>images.has(frame.image));
  const byId=new Map(frames.map(frame=>[frame.frameId,frame]));
  if(frames.length!==animation.frames.length || byId.size!==frames.length)throw new Error("원본 이미지 또는 프레임 구성이 변경되었습니다.");
  const feet={};
  const rows=animation.frames.map(({frameId,rect},index)=>{
    const frame=byId.get(frameId);
    if(!frame || ["x","y","width","height"].some(key=>frame.rect[key]!==rect[key]))throw new Error("원본 프레임 영역이 변경되었습니다.");
    if(document.coordinateMode==="foot-centers")feet[index]=frame.points;
    if(document.coordinateMode==="endpoints")feet[index]=[0,2].map(i=>({
      x:(frame.points[i].x+frame.points[i+1].x)/2,y:(frame.points[i].y+frame.points[i+1].y)/2
    }));
    return {...rect,anchorX:frame.anchor.x,anchorY:frame.anchor.y};
  });
  return {rows,feet};
}

export default function SpriteAnchorRestore({original,rows,onRestore}){
  const [items,setItems]=useState([]),[id,select]=useState(""),[review,setReview]=useState(null);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  async function list(){
    setBusy(true);setReview(null);setItems([]);select("");setNotice("");
    try{
      const result=await managementCommand("character-animation","anchor-history",{
        animation_id:original.animation.animationId,animation_version:original.animation.version
      });
      setItems(result.items);select(result.items[0]?.id || "");setNotice(result.items.length+"개 이력");
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  async function prepare(){
    setBusy(true);setNotice("");setReview(null);
    try{
      const result=await managementCommand("character-animation","anchor-load",{id});
      setReview({...restore(result.document,original),before:rows});
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  return <details><summary>앵커 이력 복원</summary><fieldset disabled={busy}>
    <button type="button" onClick={list}>좌표 이력 조회</button>
    <label>좌표 이력<select value={id} onChange={e=>{select(e.target.value);setReview(null);}}>
      {items.map(item=><option key={item.id}>{item.id}</option>)}</select></label>
    <button type="button" disabled={!id} onClick={prepare}>복원 내용 확인</button>
    {review?.before===rows && <section><p>{id} · {review.rows.length}프레임의 크롭과 앵커를 편집표에 복원합니다.</p>
      <button type="button" onClick={()=>{onRestore(review);setReview(null);setNotice("편집표에 복원했습니다.");}}>편집표에 복원</button>
      <button type="button" onClick={()=>setReview(null)}>복원 취소</button></section>}
    {notice && <p role="status">{notice}</p>}
  </fieldset></details>;
}
