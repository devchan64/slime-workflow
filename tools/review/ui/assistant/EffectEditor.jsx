import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";

const sides=["왼쪽","위쪽","오른쪽","아래쪽"];

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
    <button>정렬 저장</button></fieldset>{message && <p role="status">{message}</p>}</form>;
}

export default function EffectEditor(){
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
  return <article><h1>이펙트 좌표 검수</h1><fieldset disabled={busy}><legend>이펙트 선택</legend>
    <select aria-label="이펙트" value={selected} onChange={e=>{select(e.target.value);setDetail(null);}}>
      {effects.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select>
    <button onClick={()=>reload(n=>n+1)}>목록 새로고침</button><button disabled={!selected} onClick={load}>선택 이펙트 불러오기</button></fieldset>
    {error && <p role="alert">{error}</p>}
    {detail && <section><h2>{detail.document.name}</h2><p>{detail.document.renderer} · {detail.document.frames}프레임</p>
      <img src={detail.sheetImage} alt="이펙트 시트 원본" style={{maxWidth:"100%"}}/>
      {detail.hostImage && <img src={detail.hostImage} alt="빌보드 원본" style={{maxWidth:"100%"}}/>}
      {detail.document.renderer!=="waypoint-animation" && <Alignment detail={detail}/>}
    </section>}
  </article>;
}
