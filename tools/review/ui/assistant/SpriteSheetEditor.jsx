import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

const fields=["x","y","width","height","anchorX","anchorY"];
const labels=["X","Y","너비","높이","앵커 X","앵커 Y"];

function FrameEditor({image,frames}){
  const [rows,setRows]=useState(()=>frames.map(({rect,anchor})=>({...rect,anchorX:anchor.x,anchorY:anchor.y})));
  const [columns,setColumns]=useState(4),[busy,setBusy]=useState(false);
  const [result,setResult]=useState(null),[error,setError]=useState("");
  function update(index,field,value){
    setRows(rows.map((row,i)=>i===index?{...row,[field]:value}:row));
    setResult(null);setError("");
  }
  async function exportSheet(event){
    event.preventDefault();setBusy(true);setResult(null);setError("");
    try{
      const record=await managementCommand("character-animation","sheet-export",{
        image,columns:Number(columns),frames:rows.map(row=>Object.fromEntries(fields.map(key=>[key,Number(row[key])]))),
        sourceFrames:frames.map(({rect})=>[rect.x,rect.y,rect.width,rect.height])
      });
      if(!record.id || !record.image || !record.coordinates)throw new Error("내보낸 시트와 좌표맵을 확인할 수 없습니다.");
      setResult(record);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <form onSubmit={exportSheet}><fieldset disabled={busy}><legend>크롭과 앵커 편집</legend>
    <ResultTable table={{title:"등록 프레임 좌표",summary:frames.length+"프레임",columns:["프레임",...labels],
      rows:rows.map((row,i)=>[i+1,...fields.map((field,j)=><input aria-label={(i+1)+"번 "+labels[j]} type="number"
        required step={j<4?1:"any"} value={row[field]} onChange={e=>update(i,field,e.target.value)}/>)])}}/>
    <label>출력 열 수<input type="number" min="1" max="128" required value={columns}
      onChange={e=>{setColumns(e.target.value);setResult(null);}}/></label>
    <button>시트와 좌표맵 내보내기</button></fieldset>
    {error && <p role="alert">{error}</p>}
    {result && <section><p role="status">내보내기 완료 · {result.id}</p>
      <a href={"data:image/png;base64,"+result.image} download="sprite-sheet.png">시트 PNG 다운로드</a>{" · "}
      <a href={"data:application/json;charset=utf-8,"+encodeURIComponent(JSON.stringify(result.coordinates,null,2))} download="coordinates.json">좌표맵 JSON 다운로드</a>
    </section>}
  </form>;
}

function Sheet({path,source}){
  const [detail,setDetail]=useState(null),[error,setError]=useState("");
  useEffect(()=>{
    let active=true;
    managementCommand("character-animation","sheet-image",{path,source}).then(record=>{
      if(record.path!==path || !record.image)throw new Error("선택한 시트 원본을 확인할 수 없습니다.");
      if(active)setDetail(record);
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[path,source]);
  if(error)return <p role="alert">{error}</p>;
  if(!detail)return <p role="status">원본 시트를 불러오는 중…</p>;
  const frames=detail.animation?.frames;
  return <section><h2>{path}</h2><img src={"data:image/png;base64,"+detail.image} alt="원본 스프라이트 시트" style={{maxWidth:"100%"}}/>
    {detail.layout && <p>{detail.layout.columns}열 × {detail.layout.rows}행</p>}
    {frames?.length>0 && <FrameEditor frames={frames} image={detail.image}/>}
  </section>;
}

export default function SpriteSheetEditor(){
  const [source,setSource]=useState("assets"),[query,setQuery]=useState("");
  const [request,setRequest]=useState(null),[items,setItems]=useState(null),[selected,select]=useState("");
  const [error,setError]=useState("");
  useEffect(()=>{
    if(!request)return;
    let active=true;
    managementCommand("character-animation","sheet-search",request).then(result=>{
      if(active)setItems(result.items);
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[request]);
  function search(nextSource){
    setItems(null);setError("");select("");setRequest({source:nextSource,query});
  }
  return <article><h1>스프라이트 시트 편집기</h1>
    <form onSubmit={event=>{event.preventDefault();search(source);}}>
      <label>검색 원본<select value={source} onChange={event=>{setSource(event.target.value);search(event.target.value);}}>
        <option value="assets">에셋 스프라이트</option><option value="baseline">베이스라인 스프라이트</option></select></label>
      <label>스프라이트 검색<input value={query} onChange={event=>setQuery(event.target.value)}/></label>
      <button>원본 검색</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {request && !items && !error && <p role="status">스프라이트 검색 중…</p>}
    {items && <ResultTable table={{title:"검색 결과",summary:items.length+"개 시트",columns:["스프라이트","원본 경로"],
      rows:items.map(item=>[<button onClick={()=>select(item.path)}>{item.label}</button>,item.path])}}/>}
    {selected && <Sheet key={source+":"+selected} path={selected} source={source}/>}
  </article>;
}
