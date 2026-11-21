import React,{useEffect,useState} from "react";

export default function TownMapReview(){
  const [ready,setReady]=useState(false),[feedback,setFeedback]=useState("");
  useEffect(()=>{
    let active=true;
    const url=new URL(location.href);
    url.searchParams.set("mapKind","town");
    history.replaceState(null,"",url);
    import(new URL("/isloon-map-review/block-map-review.js",location.origin).href).then(()=>{
      if(active)setReady(true);
    }).catch(error=>{if(active)setFeedback(error.message);});
    return ()=>{active=false;};
  },[]);
  const destination=kind=>{
    const url=new URL(location.href);
    url.pathname="/management/frame/map-review/";
    url.searchParams.delete("map");url.searchParams.set("mapKind",kind);
    return url.href;
  };
  async function exportImage(){
    try{setFeedback(await window.mapReviewExportImage());}
    catch(error){setFeedback(error.message);}
  }
  return <article><nav><a href={destination("field")}>야외필드 검수</a> · <a href={destination("battle")}>전투필드 검수</a></nav>
    <h1 id="map-title">도시맵 검수</h1>
    <fieldset disabled={!ready}><legend>지도와 시점</legend>
      <label>맵 선택<select id="map-select"/></label><button id="load-map">맵 불러오기</button>
      <label>건물 선택<select id="building"><option value="">건물 선택</option></select></label>
      {[["zoom-out","축소"],["zoom-in","확대"],["actual-size","사람 중심 · 100%"],["fit","전체 보기"]].map(([id,label])=><button key={id} id={id}>{label}</button>)}
      <output id="zoom-level" aria-live="polite"/>
      {[["show-character","기본 캐릭터",true],["show-safe-boundary","결계탑 · 결계 오러",true],["edges","메시 경계",false],["tile-edges","타일 경계",false],["blocked-areas","이동금지 영역",false]].map(([id,label,checked])=>
        <label key={id}><input type="checkbox" id={id} defaultChecked={checked} onChange={()=>window.mapReviewDisplayOptions(...["show-character","show-safe-boundary","edges"].map(key=>document.getElementById(key).checked),"contrast",document.getElementById("tile-edges").checked,document.getElementById("blocked-areas").checked)}/>{label}</label>)}
      <button onClick={exportImage}>전체 맵 PNG 내보내기</button><a id="map-export-download" hidden>PNG 다운로드</a>
    </fieldset>
    <p role="status" id="status">도시맵을 불러오는 중입니다.</p>{feedback && <p role="status">{feedback}</p>}
    <canvas id="map" width="768" height="576" tabIndex="0" aria-label="도시맵 · 방향키로 이동" style={{width:"100%",aspectRatio:"4/3",touchAction:"none"}}/>
    {[["tile","지형 타일"],["building","건물 스프라이트"],["billboard","빌보드"],["structure","결계·경비 구조물"]].map(([id,label])=>
      <details key={id}><summary>{label} 원본</summary><div id={"applied-"+id+"-list"}/></details>)}
  </article>;
}
