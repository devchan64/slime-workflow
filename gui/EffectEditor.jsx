import SnapshotStatus from "./SnapshotStatus.jsx";
import React,{useEffect,useRef,useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import {validEffectDetail,validWaypointFrames} from "./effectDetailValidation.mjs";

import {drawAlignment} from "./drawAlignment.js";

function AlignmentPreview({detail,values}){
  const canvas=useRef(null);
  const [play,setPlay]=useState(true),[frame,setFrame]=useState(0),[host,setHost]=useState(true),[guides,setGuides]=useState(true);
  const [status,setStatus]=useState(""),[error,setError]=useState(""),[revision,retry]=useState(0);
  useEffect(()=>{
    const element=canvas.current;
    let active=true,timedOut=false;
    const controller=new AbortController();
    const timeout=setTimeout(()=>{timedOut=true;element.effectPreviewRevision++;controller.abort();},30000);
    setError("");setStatus("정렬 미리보기를 불러오는 중입니다.");
    untilAborted(drawAlignment(element,detail,values,play,frame,host,guides),controller.signal)
      .then(message=>{if(active)setStatus(message);})
      .catch(problem=>{if(active){setStatus("");setError(timedOut ? "정렬 미리보기 조회 시간이 초과됐습니다." : problem.message || "정렬 미리보기를 불러오지 못했습니다.");}})
      .finally(()=>clearTimeout(timeout));
    return ()=>{active=false;clearTimeout(timeout);controller.abort();element.effectPreviewRevision++;};
  },[detail,values,play,frame,host,guides,revision]);
  return <fieldset><legend>정렬 미리보기</legend>
    <label><input type="checkbox" checked={play} onChange={e=>{if(!e.target.checked)setFrame(canvas.current?.effectDisplayedFrame ?? frame);setPlay(e.target.checked);}}/>애니메이션 재생</label>
    <label>정지 프레임<input type="range" min="0" max={values.frames.length-1} value={frame} disabled={play}
      onChange={e=>setFrame(Number(e.target.value))}/></label>
    {detail.hostImage && <label><input type="checkbox" checked={host} onChange={e=>setHost(e.target.checked)}/>빌보드 표시</label>}
    <label><input type="checkbox" checked={guides} onChange={e=>setGuides(e.target.checked)}/>영역 가이드</label>
    <canvas ref={canvas} width="640" height="640" style={{width:"100%",maxWidth:640}} aria-label="정렬 미리보기"/>
    <p role="status">{status}</p>
    {error && <div role="alert"><p>{error}</p><button type="button" onClick={()=>retry(value=>value+1)}>미리보기 다시 불러오기</button></div>}
  </fieldset>;
}

const sides=["왼쪽","위쪽","오른쪽","아래쪽"];

function WaypointPreview({detail}){
  const canvas=useRef(null),displayedFrame=useRef(0);
  const [playing,setPlaying]=useState(true),[frame,setFrame]=useState(0),[guides,setGuides]=useState(true);
  const [error,setError]=useState(""),[loading,setLoading]=useState(true),[revision,retry]=useState(0);
  const frames=detail.animationMetadata?.frames;
  const validFrames=validWaypointFrames(frames,detail.document.frames);
  useEffect(()=>{
    if(!validFrames)return;
    const sheet=new Image(),ctx=canvas.current.getContext("2d");
    let active=true,request,expired=false;
    setError("");setLoading(true);ctx.clearRect(0,0,640,640);
    const timeout=setTimeout(()=>{expired=true;if(active){setLoading(false);setError("웨이포인트 시트 조회 시간이 초과됐습니다.");}},30000);
    sheet.onload=()=>{
      if(!active || expired)return;
      clearTimeout(timeout);
      setLoading(false);
      const start=performance.now();
      function draw(time){
        if(!active)return;
        const index=playing?Math.floor((time-start)*6/1000)%frames.length:frame;
        displayedFrame.current=index;
        const {rect,anchor}=frames[index];
        const left=320-anchor.x*420/rect.width,top=440-anchor.y*420/rect.height;
        ctx.fillStyle="#182329";ctx.fillRect(0,0,640,640);
        ctx.drawImage(sheet,rect.x,rect.y,rect.width,rect.height,left,top,420,420);
        if(guides){
          ctx.strokeStyle="#ff70be";ctx.strokeRect(left,top,420,420);
          ctx.strokeStyle="#ff4545";ctx.beginPath();ctx.moveTo(310,440);ctx.lineTo(330,440);
          ctx.moveTo(320,430);ctx.lineTo(320,450);ctx.stroke();
        }
        ctx.fillStyle="white";ctx.fillText(`프레임 ${index+1}/${frames.length}`,16,24);
        if(playing)request=requestAnimationFrame(draw);
      }
      draw(start);
    };
    sheet.onerror=()=>{clearTimeout(timeout);if(active && !expired){setLoading(false);setError("웨이포인트 시트를 읽지 못했습니다.");}};
    sheet.src=detail.sheetImage;
    return ()=>{active=false;clearTimeout(timeout);sheet.onload=null;sheet.onerror=null;cancelAnimationFrame(request);};
  },[detail,frames,playing,frame,guides,revision,validFrames]);
  if(!validFrames)return <p role="alert">프레임 정보를 확인할 수 없습니다. 원본을 확인한 뒤 상세를 다시 불러오세요.</p>;
  return <fieldset><legend>웨이포인트 미리보기</legend>
    <label><input type="checkbox" checked={playing} onChange={e=>{if(!e.target.checked)setFrame(displayedFrame.current);setPlaying(e.target.checked);}}/>재생</label>
    <label>프레임<input type="range" min="0" max={frames.length-1} value={frame} disabled={playing}
      onChange={e=>setFrame(Number(e.target.value))}/></label>
    <label><input type="checkbox" checked={guides} onChange={e=>setGuides(e.target.checked)}/>영역과 앵커 표시</label>
    <canvas ref={canvas} width="640" height="640" style={{width:"100%",maxWidth:640}} aria-label="웨이포인트 애니메이션"/>
    {loading && <p role="status">웨이포인트 시트를 불러오는 중입니다.</p>}
    {error && <div role="alert"><p>{error}</p><button type="button" onClick={()=>retry(value=>value+1)}>미리보기 다시 불러오기</button></div>}
  </fieldset>;
}

function WaypointReplacement({detail,onSaved,onDirtyChange,onBusyChange}){
  const [source,setSource]=useState(JSON.stringify(detail.document,null,2));
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const previewRequest=useRef(null),submitting=useRef(false);
  useEffect(()=>()=>previewRequest.current?.abort(),[]);
  useEffect(()=>{onDirtyChange(source!==JSON.stringify(detail.document,null,2));},[source,detail,onDirtyChange]);
  useEffect(()=>{onBusyChange(busy);},[busy,onBusyChange]);
  async function review(){
    if(busy || previewRequest.current)return;
    const controller=new AbortController();previewRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setError("");setBusy(true);setPending(null);
    try{
      const draft={id:detail.document.id,revision:detail.revision,effect:JSON.parse(source)};
      const result=await untilAborted(managementCommand("hermes-agent","hermes-waypoint-preview",{draft},{signal:controller.signal}),controller.signal);
      if(!/^[a-f0-9]{64}$/.test(result?.review_sha256 || "") || result.after?.id!==draft.effect.id || [result.after?.image,result.after?.animation,result.note].some(value=>typeof value!=="string"))throw new Error("교체 검토 결과를 확인할 수 없습니다.");
      setPending({draft,result,requestId:crypto.randomUUID()});
    }catch(problem){if(!controller.signal.aborted || timedOut)setError(timedOut ? "교체 검토 시간이 초과됐습니다. 다시 시도하세요." : problem instanceof SyntaxError?"새 이펙트 JSON 형식을 확인하세요.":requestErrorMessage(problem));}
    finally{clearTimeout(timeout);if(previewRequest.current===controller)previewRequest.current=null;if(!controller.signal.aborted || timedOut)setBusy(false);}
  }
  async function confirm(){
    if(submitting.current || busy || !pending)return;
    submitting.current=true;
    setError("");setBusy(true);
    try{
      const result=await managementCommand("hermes-agent","hermes-waypoint-replace",{
        request_id:pending.requestId,draft:pending.draft,review_sha256:pending.result.review_sha256
      });
      if(result.state!=="completed" || result.id!==pending.draft.effect.id)throw new Error("교체 결과 확인 필요 · 접수 "+pending.requestId);
      onSaved(result.id);
    }catch(problem){setError("교체 결과를 확인하지 못했습니다. 원본과 접수 기록을 확인하세요 · 접수 "+pending.requestId+" · "+requestErrorMessage(problem));}
    finally{submitting.current=false;setBusy(false);}
  }
  return <details><summary>웨이포인트 이펙트 교체</summary><fieldset disabled={busy}>
    <label>새 이펙트 JSON<textarea rows={10} value={source} onChange={e=>{setSource(e.target.value);setPending(null);setError("");}}/></label>
    <button onClick={review}>교체 내용 확인</button>
    {pending && <section><h3>{detail.document.id} → {pending.result.after.id}</h3>
      <p>이미지 · {pending.result.after.image}</p><p>애니메이션 · {pending.result.after.animation}</p>
      <p>{pending.result.note}</p><button onClick={confirm}>확인 후 교체</button>
      <button onClick={()=>setPending(null)}>취소</button></section>}
    {error && <p role="alert">{error}</p>}
  </fieldset>{busy && <p role="status">웨이포인트 요청을 처리하고 있습니다.</p>}</details>;
}

function Alignment({detail,onDirtyChange,onBusyChange}){
  const [values,setValues]=useState(detail.document.alignment);
  const [savedValues,setSavedValues]=useState(detail.document.alignment);
  const [revision,setRevision]=useState(detail.revision),[busy,setBusy]=useState(false),[message,setMessage]=useState("");
  const submitting=useRef(false);
  useEffect(()=>{onDirtyChange(JSON.stringify(values)!==JSON.stringify(savedValues));},[values,savedValues,onDirtyChange]);
  useEffect(()=>{onBusyChange(busy);},[busy,onBusyChange]);
  function rectangle(key,index){
    const row=key==="target"?values.target:values.frames[index];
    return sides.map((side,i)=><label key={side}>{side}<input type="number" required step="any" value={row[i]}
      onChange={e=>{
        const next=row.map((v,j)=>i===j?e.target.value:v);
        setValues({...values,[key]:key==="target"?next:values.frames.map((v,j)=>index===j?next:v)});
      }}/></label>);
  }
  async function save(event){
    event.preventDefault();if(submitting.current)return;submitting.current=true;setBusy(true);setMessage("");
    const alignment={...values,target:values.target.map(Number),alpha:Number(values.alpha),
      frames:values.frames.map(row=>row.map(v=>Math.round(Number(v)*100)/100))};
    try{
      const result=await managementCommand("map-assets","effect-save",{id:detail.document.id,expectedRevision:revision,requestId:crypto.randomUUID(),alignment});
      if(!result.revision)throw new Error("저장된 리비전을 확인할 수 없습니다.");
      setRevision(result.revision);setValues(alignment);setSavedValues(alignment);setMessage("이펙트 정렬을 저장했습니다.");
    }catch(problem){setMessage("저장 결과를 확인하지 못했습니다. 다시 저장하기 전에 원본과 이력을 확인하세요. · "+requestErrorMessage(problem));}
    finally{submitting.current=false;setBusy(false);}
  }
  return <form onSubmit={save}><fieldset disabled={busy}><legend>공용 이펙트 정렬</legend>
    <fieldset><legend>대상 영역</legend>{rectangle("target")}</fieldset>
    <label>불투명도<input type="number" min="0" max="1" step="any" required value={values.alpha} onChange={e=>setValues({...values,alpha:e.target.value})}/></label>
    {values.frames.map((_,index)=><fieldset key={index}><legend>{index+1}번 프레임</legend>{rectangle("frames",index)}</fieldset>)}
    <AlignmentPreview detail={detail} values={values}/><button>정렬 저장</button></fieldset>{message && <p role="status">{message}</p>}</form>;
}

export default function EffectEditor(){
  const [notice,setNotice]=useState("");
  const [effects,setEffects]=useState([]),[selected,select]=useState(""),[detail,setDetail]=useState(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[revision,reload]=useState(0);
  const [detailLoading,setDetailLoading]=useState(false);
  const [dirty,setDirty]=useState(false),[editorBusy,setEditorBusy]=useState(false),[editorVersion,setEditorVersion]=useState(0);
  const detailRequest=useRef(null);
  useEffect(()=>()=>{const request=detailRequest.current;detailRequest.current=null;request?.abort();},[]);
  useEffect(()=>{
    let active=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),30000);
    setBusy(true);setError("");
    untilAborted(managementCommand("map-assets","effect-list",{},{signal:controller.signal}),controller.signal).then(result=>{
      if(!Array.isArray(result?.effects) || result.effects.some(item=>!item || typeof item.id!=="string" || typeof item.name!=="string"))throw new Error("이펙트 목록 응답을 확인할 수 없습니다.");
      if(active){setEffects(result.effects);select(old=>old || result.effects[0]?.id || "");}
    }).catch(problem=>{if(active)setError(problem?.name==="AbortError" ? "이펙트 목록 조회 시간이 초과됐습니다. 목록을 새로고침하세요." : problem instanceof TypeError ? "이펙트 목록 서버에 연결하지 못했습니다. 목록을 새로고침하세요." : problem.message);}).finally(()=>{clearTimeout(timeout);if(active)setBusy(false);});
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[revision]);
  async function load(){
    setBusy(true);setDetailLoading(true);setError("");
    const controller=new AbortController();detailRequest.current=controller;
    const timeout=setTimeout(()=>controller.abort(),30000);
    try{
      const result=await untilAborted(managementCommand("map-assets","effect-load",{id:selected},{signal:controller.signal}),controller.signal);
      if(!validEffectDetail(result,selected))throw new Error("선택한 이펙트의 상세 응답을 확인할 수 없습니다.");
      if(detailRequest.current===controller){setDetail(result);setEditorVersion(value=>value+1);}
    }catch(problem){if(detailRequest.current===controller)setError(problem?.name==="AbortError" ? "이펙트 조회 시간이 초과됐습니다. 다시 불러오세요." : problem instanceof TypeError ? "이펙트 서버에 연결하지 못했습니다. 다시 불러오세요." : problem.message);}
    finally{clearTimeout(timeout);if(detailRequest.current===controller){detailRequest.current=null;setDetailLoading(false);setBusy(false);}}
  }
  return <article className="effect-editor-page"><h1>이펙트 좌표 검수</h1><fieldset className="effect-editor-picker" disabled={busy || editorBusy}><legend>이펙트 선택</legend>
    <select aria-label="이펙트" disabled={dirty} value={selected} onChange={e=>{select(e.target.value);setDetail(null);}}>
      {selected && !effects.some(item=>item.id===selected) && <option value={selected}>{selected} · 현재 목록에 없음</option>}
      {!effects.length && <option value="">{busy ? "목록 조회 중…" : error ? "이펙트 목록 조회 실패" : "선택할 이펙트가 없습니다"}</option>}
      {effects.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select>
    <button onClick={()=>reload(n=>n+1)}>목록 새로고침</button><button disabled={dirty || !effects.some(item=>item.id===selected)} onClick={load}>선택 이펙트 불러오기</button></fieldset>
    {error && <p role="alert">{error}</p>}
    {error && effects.length>0 && <p role="status">이전 조회의 목록{detail ? "과 열려 있는 상세를" : "을"} 유지합니다.</p>}
    {selected && !busy && !error && !effects.some(item=>item.id===selected) && <p role="status">선택한 이펙트가 현재 목록에 없습니다. 다른 이펙트를 선택할 수 있습니다.</p>}
    {notice && <p role="status">{notice}</p>}
    {detailLoading && detail && <p role="status">상세를 다시 읽는 중입니다. 아래는 마지막 조회 결과입니다.</p>}
    {dirty && <p role="status">저장하지 않은 편집이 있습니다. 다른 이펙트를 선택하려면 저장하거나 편집을 취소하세요. <button type="button" disabled={editorBusy} onClick={()=>{setDirty(false);setEditorVersion(n=>n+1);}}>편집 취소</button></p>}
    {detail && <section><h2>{detail.document.name}</h2><p>{detail.document.renderer} · {detail.document.frames}프레임</p><fieldset disabled={detailLoading} style={{border:0,padding:0,margin:0}} aria-label="이펙트 상세와 편집">
      <img src={detail.sheetImage} alt="이펙트 시트 원본" style={{maxWidth:"100%"}}/>
      {detail.hostImage && <img src={detail.hostImage} alt="빌보드 원본" style={{maxWidth:"100%"}}/>}
      {detail.document.renderer==="waypoint-animation"?<><WaypointPreview detail={detail}/><WaypointReplacement key={editorVersion} detail={detail} onDirtyChange={setDirty} onBusyChange={setEditorBusy} onSaved={id=>{setDirty(false);setEditorBusy(false);setNotice("웨이포인트 교체 완료 · "+id);select(id);setDetail(null);reload(n=>n+1);}}/></>:<Alignment key={editorVersion} detail={detail} onDirtyChange={setDirty} onBusyChange={setEditorBusy}/>}
    </fieldset></section>}
    <SnapshotStatus/>
  </article>;
}
