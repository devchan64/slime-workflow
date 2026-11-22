import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";
import {restoreSpriteAnchors} from "./spriteAnchorRestore.mjs";


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
  async function save(){
    setBusy(true);setReview(null);setNotice("");
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
        return {frameId,rect,direction,image,anchor,points:[anchor]};
      });
      const document={schemaVersion:1,artifactType:"character-animation-anchor-review",coordinateMode:"anchor",
        description:"스프라이트 시트 편집기에서 저장한 현재 시트 앵커",frames,
        source:{animationId:animation.animationId,animationVersion:animation.version,sheets:[{image,sha256:original.imageSha256}]}};
      const saved=await managementCommand("character-animation","anchor-save",{document});
      if(!saved.id)throw new Error("저장된 앵커 이력 ID를 확인할 수 없습니다.");
      setItems(previous=>[{id:saved.id},...previous.filter(item=>item.id!==saved.id)]);
      select(saved.id);setNotice("앵커 이력 저장 완료 · "+saved.id);
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  async function prepare(){
    setBusy(true);setNotice("");setReview(null);
    try{
      const result=await managementCommand("character-animation","anchor-load",{id});
      setReview({...restoreSpriteAnchors(result.document,original),before:rows});
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  return <details><summary>앵커 이력 저장·복원</summary><fieldset disabled={busy}>
    <button type="button" onClick={save}>현재 앵커를 이력으로 저장</button>
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
