import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";

const fields=[
  ["anchorX","앵커 X",0,16],["anchorY","앵커 Y",0,16],
  ["displayWidthAdjustment","가로 크기 보정 (px)",-2048,2048,1],
  ["displayHeightAdjustment","세로 크기 보정 (px)",-2048,2048,1],
  ["shadowOffsetColumn","그림자 열 이동 (타일)",-4,4],["shadowOffsetRow","그림자 행 이동 (타일)",-4,4],
  ["shadowScaleX","그림자 열 배율",0.1,4],["shadowScaleY","그림자 행 배율",0.1,4],
];

function BuildingProperties({building,generation,busy,setBusy,onSaved}){
  const expected={displayWidthAdjustment:0,displayHeightAdjustment:0,...building.properties};
  const original={shadowShape:"circle",shadowOffsetColumn:0,shadowOffsetRow:0,shadowScaleX:1,shadowScaleY:1,...expected};
  const [values,edit]=useState(original),[error,setError]=useState("");
  const changed=Object.entries(original).some(([key,value])=>values[key]!=="" && String(values[key])!==String(value));
  async function save(event){
    event.preventDefault();
    if(!changed || busy)return;
    const properties={shadowShape:values.shadowShape};
    for(const [key] of fields)properties[key]=Number(values[key]);
    for(const usage of building.maps){
      const width=usage.tower?building.width*112/207:(usage.width+usage.height)*40*1.04/usage.contentWidth;
      if(width+properties.displayWidthAdjustment<=0 || width*building.height/building.width+properties.displayHeightAdjustment<=0){
        setError(usage.map+"에서 표시 크기가 0 이하입니다.");return;
      }
    }
    setBusy(true);setError("");
    try{
      await managementCommand("map-assets","building-save",{texture:building.texture,generation,expected,properties});
      onSaved(building.texture);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <form onSubmit={save}><fieldset disabled={busy}><legend>건물 표시 속성</legend>
    {fields.map(([key,label,min,max,step])=><label key={key}>{label}<input type="number" required min={min} max={max} step={step || "any"} value={values[key]} onChange={e=>edit({...values,[key]:e.target.value})}/></label>)}
    <label>그림자 형태<select value={values.shadowShape} onChange={e=>edit({...values,shadowShape:e.target.value})}>
      <option value="circle">원형</option><option value="rectangle">사각형</option></select></label>
    <button type="button" onClick={()=>edit({...values,displayWidthAdjustment:0,displayHeightAdjustment:0})}>크기 보정 초기화</button>
    <button disabled={!changed}>표시 속성 저장</button>
    {error && <p role="alert">{error}</p>}
  </fieldset></form>;
}

async function buildingCommand(action,payload){
  const bytes=new TextEncoder().encode(JSON.stringify(payload));
  const digest=new Uint8Array(await crypto.subtle.digest("SHA-256",bytes));
  const requestId="building-"+action+"-"+Array.from(digest,b=>b.toString(16).padStart(2,"0")).join("");
  return managementCommand("map-assets","building-"+action,{...payload,requestId});
}

function BuildingRegistration({generation,busy,setBusy,onRegistered}){
  const [error,setError]=useState("");
  async function submit(event){
    event.preventDefault();
    const form=event.currentTarget,fields=new FormData(form),file=fields.get("image");
    if(busy)return;
    setBusy(true);setError("");
    try{
      if(!file.size || file.size>16*1024*1024)throw new Error("16MiB 이하의 PNG를 선택하세요.");
      const imageBase64=await new Promise((resolve,reject)=>{
        const reader=new FileReader();
        reader.onload=()=>resolve(reader.result.split(",")[1]);
        reader.onerror=()=>reject(new Error("이미지를 읽을 수 없습니다."));
        reader.readAsDataURL(file);
      });
      const texture=fields.get("texture").trim();
      await buildingCommand("register",{texture,generation,imageBase64,properties:{anchorX:Number(fields.get("x")),anchorY:Number(fields.get("y"))}});
      onRegistered(texture);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <details><summary>건물 등록</summary><form onSubmit={submit}><fieldset disabled={busy}>
    <label>건물 ID<input name="texture" required pattern="town-[a-z0-9\x2d]+-v[1-9][0-9]*" placeholder="town-iseulon-house-v1"/></label>
    <label>투명 PNG<input name="image" required type="file" accept="image/png"/></label>
    {[["x","앵커 X",0.5],["y","앵커 Y",1]].map(([name,label,value])=><label key={name}>{label}<input name={name} type="number" required min="0" max="16" step="any" defaultValue={value}/></label>)}
    <button>건물 등록</button>{error && <p role="alert">{error}</p>}
  </fieldset></form></details>;
}

export default function BuildingEditor(){
  const [catalog,setCatalog]=useState(null),[selected,setSelected]=useState("");
  const [error,setError]=useState(""),[revision,reload]=useState(0);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  useEffect(()=>{
    let active=true;
    setCatalog(null);setError("");
    managementCommand("map-assets","building-list",{}).then(result=>{
      if(active){
        setCatalog(result);
        setSelected(previous=>result.assets.some(row=>row.texture===previous)?previous:result.assets[0]?.texture || "");
      }
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[revision]);
  const building=catalog?.assets.find(item=>item.texture===selected);
  async function retire(){
    if(busy || !building || building.texture==="ward-tower-v1" || building.maps.length)return;
    if(!window.confirm(building.texture+"을 건물 목록과 공용 속성에서 삭제할까요? 이미지 원본과 등록 이력은 보존됩니다."))return;
    setBusy(true);setError("");
    try{
      await buildingCommand("retire",{texture:building.texture,generation:catalog.generation});
      setNotice(building.texture+" 삭제 완료");reload(value=>value+1);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  const image=id=>"/management/assistant/building-image/"+encodeURIComponent(id);
  return <article><h1>건물 에셋 관리</h1>
    <button disabled={busy} onClick={()=>reload(value=>value+1)}>건물 목록 다시 읽기</button>
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
    {catalog ? <><p>건물 {catalog.assets.length}종 · DB 세대 {catalog.generation}</p>
      <BuildingRegistration generation={catalog.generation} busy={busy} setBusy={setBusy} onRegistered={id=>{
        setNotice(id+" 등록 완료");setSelected(id);reload(value=>value+1);
      }}/>
      <div aria-label="건물 목록">{catalog.assets.map(item=><button key={item.texture} disabled={busy} aria-pressed={item.texture===selected} onClick={()=>setSelected(item.texture)}>
        <img loading="lazy" src={image(item.texture)} width="64" height="64" style={{objectFit:"contain"}} alt=""/>{item.texture}</button>)}</div>
    </> : !error && <p role="status">건물 목록을 읽고 있습니다.</p>}
    {building && <section><h2>{building.texture}</h2>
      <img src={image(selected)} alt={selected+" 원본"} style={{maxWidth:"100%"}}/>
      <p>{building.width}×{building.height} px · 앵커 X {building.properties.anchorX} · Y {building.properties.anchorY}</p>
      <BuildingProperties key={building.texture} building={building} generation={catalog.generation} busy={busy} setBusy={setBusy}
        onSaved={id=>{setNotice(id+" 표시 속성을 저장했습니다.");reload(value=>value+1);}}/>
      <h3>사용 맵</h3>{building.maps.length ? <ul>{building.maps.map((usage,i)=><li key={i}>{usage.map} · {usage.name} · {usage.width}×{usage.height} · {usage.facing}</li>)}</ul> : <p>사용 맵 없음</p>}
      <button disabled={busy || building.texture==="ward-tower-v1" || !!building.maps.length} onClick={retire}>선택 건물 삭제</button>
    </section>}
  </article>;
}
