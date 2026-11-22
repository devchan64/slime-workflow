import SnapshotStatus from "./SnapshotStatus.jsx";
import React,{useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";

import {drawAlignment} from "./drawAlignment.js";

function AlignmentPreview({detail,values}){
  const canvas=useRef(null);
  const [play,setPlay]=useState(true),[frame,setFrame]=useState(0),[host,setHost]=useState(true),[guides,setGuides]=useState(true);
  const [status,setStatus]=useState("");
  useEffect(()=>{
    const element=canvas.current;
    let active=true;
    drawAlignment(element,detail,values,play,frame,host,guides)
      .then(message=>{if(active)setStatus(message);})
      .catch(error=>{if(active)setStatus(error.message);});
    return ()=>{active=false;element.effectPreviewRevision++;};
  },[detail,values,play,frame,host,guides]);
  return <fieldset><legend>정렬 미리보기</legend>
    <label><input type="checkbox" checked={play} onChange={e=>setPlay(e.target.checked)}/>애니메이션 재생</label>
    <label>정지 프레임<input type="range" min="0" max={values.frames.length-1} value={frame} disabled={play}
      onChange={e=>setFrame(Number(e.target.value))}/></label>
    {detail.hostImage && <label><input type="checkbox" checked={host} onChange={e=>setHost(e.target.checked)}/>빌보드 표시</label>}
    <label><input type="checkbox" checked={guides} onChange={e=>setGuides(e.target.checked)}/>영역 가이드</label>
    <canvas ref={canvas} width="640" height="640" style={{width:"100%",maxWidth:640}} aria-label="정렬 미리보기"/>
    <p role="status">{status}</p>
  </fieldset>;
}

const sides=["왼쪽","위쪽","오른쪽","아래쪽"];

function WaypointPreview({detail}){
  const canvas=useRef(null);
  const [playing,setPlaying]=useState(true),[frame,setFrame]=useState(0),[guides,setGuides]=useState(true);
  const [error,setError]=useState("");
  const frames=detail.animationMetadata?.frames;
  useEffect(()=>{
    if(!frames?.length || frames.length!==detail.document.frames)return;
    const sheet=new Image(),ctx=canvas.current.getContext("2d");
    let active=true,request;
    setError("");
    sheet.onload=()=>{
      const start=performance.now();
      function draw(time){
        if(!active)return;
        const index=playing?Math.floor((time-start)*6/1000)%frames.length:frame;
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
    sheet.onerror=()=>{if(active)setError("웨이포인트 시트를 읽지 못했습니다.");};
    sheet.src=detail.sheetImage;
    return ()=>{active=false;cancelAnimationFrame(request);};
  },[detail,frames,playing,frame,guides]);
  if(!frames?.length || frames.length!==detail.document.frames)return <p role="alert">프레임 정보를 확인할 수 없습니다.</p>;
  return <fieldset><legend>웨이포인트 미리보기</legend>
    <label><input type="checkbox" checked={playing} onChange={e=>setPlaying(e.target.checked)}/>재생</label>
    <label>프레임<input type="range" min="0" max={frames.length-1} value={frame} disabled={playing}
      onChange={e=>setFrame(Number(e.target.value))}/></label>
    <label><input type="checkbox" checked={guides} onChange={e=>setGuides(e.target.checked)}/>영역과 앵커 표시</label>
    <canvas ref={canvas} width="640" height="640" style={{width:"100%",maxWidth:640}} aria-label="웨이포인트 애니메이션"/>
    {error && <p role="alert">{error}</p>}
  </fieldset>;
}

function WaypointReplacement({detail,onSaved}){
  const [source,setSource]=useState(JSON.stringify(detail.document,null,2));
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  async function review(){
    setError("");setBusy(true);setPending(null);
    try{
      const draft={id:detail.document.id,revision:detail.revision,effect:JSON.parse(source)};
      const result=await managementCommand("hermes-agent","hermes-waypoint-preview",{draft});
      if(!result.review_sha256 || !result.after)throw new Error("교체 검토 결과를 확인할 수 없습니다.");
      setPending({draft,result,requestId:crypto.randomUUID()});
    }catch(problem){setError(problem instanceof SyntaxError?"새 이펙트 JSON 형식을 확인하세요.":problem.message);}
    finally{setBusy(false);}
  }
  async function confirm(){
    setError("");setBusy(true);
    try{
      const result=await managementCommand("hermes-agent","hermes-waypoint-replace",{
        request_id:pending.requestId,draft:pending.draft,review_sha256:pending.result.review_sha256
      });
      if(result.state!=="completed" || result.id!==pending.draft.effect.id)throw new Error("교체 결과 확인 필요 · 접수 "+pending.requestId);
      onSaved(result.id);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <details><summary>웨이포인트 이펙트 교체</summary><fieldset disabled={busy}>
    <label>새 이펙트 JSON<textarea rows={10} value={source} onChange={e=>{setSource(e.target.value);setPending(null);setError("");}}/></label>
    <button onClick={review}>교체 내용 확인</button>
    {pending && <section><h3>{detail.document.id} → {pending.result.after.id}</h3>
      <p>이미지 · {pending.result.after.image}</p><p>애니메이션 · {pending.result.after.animation}</p>
      <p>{pending.result.note}</p><button onClick={confirm}>확인 후 교체</button>
      <button onClick={()=>setPending(null)}>취소</button></section>}
    {error && <p role="alert">{error}</p>}
  </fieldset></details>;
}

function Alignment({detail}){
  const [values,setValues]=useState(detail.document.alignment);
  const [revision,setRevision]=useState(detail.revision),[busy,setBusy]=useState(false),[message,setMessage]=useState("");
  function rectangle(key,index){
    const row=key==="target"?values.target:values.frames[index];
    return sides.map((side,i)=><label key={side}>{side}<input type="number" required step="any" value={row[i]}
      onChange={e=>{
        const next=row.map((v,j)=>i===j?e.target.value:v);
        setValues({...values,[key]:key==="target"?next:values.frames.map((v,j)=>index===j?next:v)});
      }}/></label>);
  }
  async function save(event){
    event.preventDefault();setBusy(true);setMessage("");
    const alignment={...values,target:values.target.map(Number),alpha:Number(values.alpha),
      frames:values.frames.map(row=>row.map(v=>Math.round(Number(v)*100)/100))};
    try{
      const result=await managementCommand("map-assets","effect-save",{id:detail.document.id,expectedRevision:revision,requestId:crypto.randomUUID(),alignment});
      if(!result.revision)throw new Error("저장된 리비전을 확인할 수 없습니다.");
      setRevision(result.revision);setValues(alignment);setMessage("이펙트 정렬을 저장했습니다.");
    }catch(problem){setMessage(problem.message);}
    finally{setBusy(false);}
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
  useEffect(()=>{
    let active=true;setBusy(true);setError("");setDetail(null);setEffects([]);
    managementCommand("map-assets","effect-list",{}).then(result=>{
      if(active){setEffects(result.effects);select(old=>result.effects.some(e=>e.id===old)?old:result.effects[0]?.id || "");}
    }).catch(problem=>{if(active)setError(problem.message);}).finally(()=>{if(active)setBusy(false);});
    return ()=>{active=false;};
  },[revision]);
  async function load(){
    setBusy(true);setError("");setDetail(null);
    try{
      const result=await managementCommand("map-assets","effect-load",{id:selected});
      if(result.document?.id!==selected)throw new Error("선택한 이펙트와 응답이 일치하지 않습니다.");
      setDetail(result);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <article className="effect-editor-page"><h1>이펙트 좌표 검수</h1><fieldset className="effect-editor-picker" disabled={busy}><legend>이펙트 선택</legend>
    <select aria-label="이펙트" value={selected} onChange={e=>{select(e.target.value);setDetail(null);}}>
      {!effects.length && <option value="">{busy ? "목록 조회 중…" : error ? "이펙트 목록 조회 실패" : "선택할 이펙트가 없습니다"}</option>}
      {effects.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select>
    <button onClick={()=>reload(n=>n+1)}>목록 새로고침</button><button disabled={!effects.some(item=>item.id===selected)} onClick={load}>선택 이펙트 불러오기</button></fieldset>
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {detail && <section><h2>{detail.document.name}</h2><p>{detail.document.renderer} · {detail.document.frames}프레임</p>
      <img src={detail.sheetImage} alt="이펙트 시트 원본" style={{maxWidth:"100%"}}/>
      {detail.hostImage && <img src={detail.hostImage} alt="빌보드 원본" style={{maxWidth:"100%"}}/>}
      {detail.document.renderer==="waypoint-animation"?<><WaypointPreview detail={detail}/><WaypointReplacement detail={detail} onSaved={id=>{setNotice("웨이포인트 교체 완료 · "+id);select(id);reload(n=>n+1);}}/></>:<Alignment detail={detail}/>}
    </section>}
    <SnapshotStatus/>
  </article>;
}
