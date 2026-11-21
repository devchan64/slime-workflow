import React,{useEffect,useRef,useState} from "react";

const groundModule="/isloon-map-review/source-size-preview.js";
const rendererModule="/management/assistant/field-renderer.mjs";

async function loadImage(url){
  const image=new Image();
  image.src=url;
  await image.decode();
  return image;
}

export default function BillboardGroundPreview({source,edits}){
  const canvas=useRef(null),[assets,setAssets]=useState(null),[error,setError]=useState("");
  const [zoom,setZoom]=useState(2),[blocking,setBlocking]=useState(true),[guides,setGuides]=useState(true);
  const [character,setCharacter]=useState(true),[summary,setSummary]=useState("");
  useEffect(()=>{
    let active=true;
    async function load(){
      setAssets(null);setError("");
      const [ground,renderer,image]=await Promise.all([import(groundModule),import(rendererModule),
        loadImage("/management/map-assets/billboards/"+encodeURIComponent(source.texture)+".png")]);
      let person=null;
      if(character){
        const response=await fetch("/isloon-map-review/review-character.json");
        if(!response.ok)throw new Error("캐릭터 기준 이미지를 불러올 수 없습니다.");
        const record=await response.json();
        person={record,image:await loadImage(new URL(record.image,response.url))};
      }
      if(active)setAssets({ground,renderer,image,person});
    }
    load().catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[source,character]);
  useEffect(()=>{
    if(!assets)return;
    const values={...source.properties,...edits};
    for(const key of Object.keys(edits)){
      if(key!=="billboardBlocksMovement" && key!=="billboardPlacementAnchor")values[key]=edits[key]===""?NaN:Number(edits[key]);
    }
    if(source.initial)Object.assign(values,{billboardAnchorMode:"tile-intersection",shadowSizeVersion:2,shadowCoordinateVersion:2});
    if(Object.values(values).some(v=>typeof v==="number" && !Number.isFinite(v)) ||
      ![values.groundFootprintRows,values.groundFootprintColumns].every(v=>Number.isInteger(v)&&v>=1&&v<=8) ||
      !(values.displayHeight>0&&values.displayHeight<=1024) || Math.abs(values.anchorX)>16 || Math.abs(values.anchorY)>16){
      canvas.current.width=0;setSummary("앵커·점유·표시 높이의 입력 범위를 확인하세요.");return;
    }
    try{
      const result=assets.ground.drawAssetGroundPreview(canvas.current,assets.image,values,{
        ...assets.renderer.resolveMapRenderOptions(),previewZoom:zoom,characterPreview:assets.person,
        showBlockedAreas:blocking,showHeightGuidelines:guides,drawShadow:assets.renderer.drawBillboardContactShadow
      });
      setSummary(`실제 점유 ${result.occupiedCells}칸 · 표시 ${result.width.toFixed(1)} × ${result.height.toFixed(1)} px`);
    }catch(problem){canvas.current.width=0;setSummary(problem.message);}
  },[source,edits,assets,zoom,blocking,guides]);
  return <fieldset><legend>빌보드 배치 미리보기</legend>
    <label>확대 배율 {zoom}배<input type="range" min=".5" max="4" step=".5" value={zoom} onChange={e=>setZoom(Number(e.target.value))}/></label>
    <label><input type="checkbox" checked={character} onChange={e=>setCharacter(e.target.checked)}/>캐릭터 보기</label>
    <label><input type="checkbox" checked={blocking} onChange={e=>setBlocking(e.target.checked)}/>통행 차단 표시</label>
    <label><input type="checkbox" checked={guides} onChange={e=>setGuides(e.target.checked)}/>높이 기준선</label>
    <canvas ref={canvas} hidden={!assets} aria-label="빌보드 점유와 그림자" style={{maxWidth:"100%"}}/>
    <p role="status">{error || (assets?summary:"원본과 렌더러를 불러오는 중…")}</p>
  </fieldset>;
}
