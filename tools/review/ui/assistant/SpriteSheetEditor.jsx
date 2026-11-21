import React,{useEffect,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

const fields=["x","y","width","height","anchorX","anchorY"];
const labels=["X","Y","너비","높이","앵커 X","앵커 Y"];

function FrameEditor({image,frames}){
  const [rows,setRows]=useState(()=>frames.map(({rect,anchor})=>({...rect,anchorX:anchor.x,anchorY:anchor.y})));
  const [columns,setColumns]=useState(4),[busy,setBusy]=useState(false);
  const [result,setResult]=useState(null),[error,setError]=useState("");
  const [first,setFirst]=useState(1),[last,setLast]=useState(rows.length),[fps,setFps]=useState(6);
  function update(index,field,value){
    setRows(rows.map((row,i)=>i===index?{...row,[field]:value}:row));
    setResult(null);setError("");
  }
  async function exportSheet(event){
    event.preventDefault();setBusy(true);setResult(null);setError("");
    try{
      const gif=event.nativeEvent.submitter?.value==="gif";
      const start=gif?Number(first)-1:0,end=gif?Number(last):rows.length;
      if(!Number.isInteger(start)||!Number.isInteger(end)||start<0||end<=start||end>rows.length){
        throw new Error("GIF 시작·끝 프레임은 시트 범위 안의 정수여야 합니다.");
      }
      const payload={image,columns:gif?4:Number(columns),
        frames:rows.slice(start,end).map(row=>Object.fromEntries(fields.map(key=>[key,Number(row[key])]))),
        sourceFrames:frames.slice(start,end).map(({rect})=>[rect.x,rect.y,rect.width,rect.height])
      };
      if(gif)payload.fps=Number(fps);
      const record=await managementCommand("character-animation",gif?"sheet-gif":"sheet-export",payload);
      if(!record.id || (gif?!record.gif:!record.image || !record.coordinates))throw new Error("내보내기 결과를 확인할 수 없습니다.");
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
    <button>시트와 좌표맵 내보내기</button>
    <fieldset onChange={()=>{setResult(null);setError("");}}><legend>GIF 내보내기</legend>
      <label>시작 프레임<input type="number" value={first} onChange={e=>setFirst(e.target.value)}/></label>
      <label>끝 프레임<input type="number" value={last} onChange={e=>setLast(e.target.value)}/></label>
      <label>재생 속도 (FPS)<select value={fps} onChange={e=>setFps(e.target.value)}>
        {[4,6,8,12,16,24,30].map(rate=><option key={rate}>{rate}</option>)}</select></label>
      <button value="gif">선택 범위 GIF 내보내기</button>
    </fieldset></fieldset>
    {error && <p role="alert">{error}</p>}
    {result && <section><p role="status">내보내기 완료 · {result.id}</p>
      {result.gif?<><p>{result.frameCount}프레임 · 프레임당 {result.durationMs}ms</p>
        <a download="preview.gif" href={"data:image/gif;base64,"+result.gif}>GIF 다운로드</a></>:<><a href={"data:image/png;base64,"+result.image} download="sprite-sheet.png">시트 PNG 다운로드</a>{" · "}
      <a href={"data:application/json;charset=utf-8,"+encodeURIComponent(JSON.stringify(result.coordinates,null,2))} download="coordinates.json">좌표맵 JSON 다운로드</a></>}
    </section>}
  </form>;
}

function gridEdges(size,count){
  return Array.from({length:count+1},(_,index)=>{
    const boundary=size*index/count,lower=Math.floor(boundary);
    // Match the Python editor's round-to-even rule for half-pixel boundaries.
    return boundary-lower===0.5?lower+(lower%2):Math.round(boundary);
  });
}

function GridEditor({detail,size}){
  const [columns,setColumns]=useState(detail.layout?.columns ?? 4),[rows,setRows]=useState(detail.layout?.rows ?? 2);
  const [grid,setGrid]=useState(null),[error,setError]=useState("");
  function split(event){
    event.preventDefault();
    const cols=Number(columns),lines=Number(rows);
    if(!size || cols*lines>128 || cols>size.width || lines>size.height){
      setError("최대 128프레임이며 각 셀은 최소 1픽셀이어야 합니다.");return;
    }
    const xs=gridEdges(size.width,cols),ys=gridEdges(size.height,lines);
    const frames=[];
    for(let row=0;row<lines;row++){
      for(let col=0;col<cols;col++){
        const width=xs[col+1]-xs[col],height=ys[row+1]-ys[row];
        frames.push({rect:{x:xs[col],y:ys[row],width,height},anchor:{x:Math.floor(width/2),y:height-1}});
      }
    }
    setGrid({key:cols+"x"+lines,frames});setError("");
  }
  return <><form onSubmit={split}><fieldset><legend>원본 시트 분할</legend>
    <label>원본 열<input type="number" min="1" max="128" required value={columns} onChange={e=>setColumns(e.target.value)}/></label>
    <label>원본 행<input type="number" min="1" max="128" required value={rows} onChange={e=>setRows(e.target.value)}/></label>
    <button disabled={!size}>프레임 나누기</button>
    {error && <p role="alert">{error}</p>}</fieldset></form>
    {grid && <FrameEditor key={grid.key} frames={grid.frames} image={detail.image}/>}</>;
}

function Sheet({path,source}){
  const [size,setSize]=useState(null);
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
  return <section><h2>{path}</h2><img src={"data:image/png;base64,"+detail.image} onLoad={e=>setSize({width:e.target.naturalWidth,height:e.target.naturalHeight})} alt="원본 스프라이트 시트" style={{maxWidth:"100%"}}/>
    {detail.layout && <p>{detail.layout.columns}열 × {detail.layout.rows}행</p>}
    {frames?.length>0?<FrameEditor frames={frames} image={detail.image}/>:<GridEditor detail={detail} size={size}/>}
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
