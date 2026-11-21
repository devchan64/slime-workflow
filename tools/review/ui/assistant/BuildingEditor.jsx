import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";

export default function BuildingEditor(){
  const [catalog,setCatalog]=useState(null),[selected,setSelected]=useState("");
  const [error,setError]=useState(""),[revision,reload]=useState(0);
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
  const image=id=>"/management/assistant/building-image/"+encodeURIComponent(id);
  return <article><h1>건물 에셋 관리</h1>
    <button onClick={()=>reload(value=>value+1)}>건물 목록 다시 읽기</button>
    {error && <p role="alert">{error}</p>}
    {catalog ? <><p>건물 {catalog.assets.length}종 · DB 세대 {catalog.generation}</p>
      <div aria-label="건물 목록">{catalog.assets.map(item=><button key={item.texture} aria-pressed={item.texture===selected} onClick={()=>setSelected(item.texture)}>
        <img loading="lazy" src={image(item.texture)} width="64" height="64" style={{objectFit:"contain"}} alt=""/>{item.texture}</button>)}</div>
    </> : !error && <p role="status">건물 목록을 읽고 있습니다.</p>}
    {building && <section><h2>{building.texture}</h2>
      <img src={image(selected)} alt={selected+" 원본"} style={{maxWidth:"100%"}}/>
      <p>{building.width}×{building.height} px · 앵커 X {building.properties.anchorX} · Y {building.properties.anchorY}</p>
      <h3>사용 맵</h3>{building.maps.length ? <ul>{building.maps.map((usage,i)=><li key={i}>{usage.map} · {usage.name} · {usage.width}×{usage.height} · {usage.facing}</li>)}</ul> : <p>사용 맵 없음</p>}
    </section>}
  </article>;
}
