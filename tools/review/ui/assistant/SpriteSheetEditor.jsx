import React,{useEffect,useRef,useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

import editSpriteFrames from "./editSpriteFrames.mjs";
import applySpriteCanvas from "./applySpriteCanvas.mjs";
import renderSpritePreview from "./renderSpritePreview.mjs";

const fields=["x","y","width","height","anchorX","anchorY"];
const labels=["X","Y","너비","높이","앵커 X","앵커 Y"];

function SpritePreview({rows,image,bounds,fps,original,onEdit,canvas,onReferenceEdit}){
  const [gameSize,setGameSize]=useState(false),[guide,setGuide]=useState(true),[feet,setFeet]=useState(false);
  const [referenceHeight,setReferenceHeight]=useState(original?.runtimeDimensions?.referenceBodyHeight ?? original?.animation?.referenceBodyHeight ?? "");
  const [gameHeight,setGameHeight]=useState(original?.runtimeDimensions?.gameBodyHeight ?? original?.animation?.gameBodyHeight ?? "");
  const [previewStatus,setPreviewStatus]=useState("");
  const [mode,setMode]=useState("크롭"),[target,setTarget]=useState("현재 프레임"),[selection,setSelection]=useState([]);
  const [notice,setNotice]=useState(""),[revision,refresh]=useState(0);
  function togglePlayback(){
    if(playing)setFrame((canvas.current?.spriteEditorState?.displayedIndex ?? frame-1)+1);
    setPlaying(!playing);
  }
  function selectClip(id){
    const animation=original.animation;
    const selected=animation.clips.find(item=>item.clipId===id);
    const first=animation.frames.findIndex(item=>item.frameId===selected?.frames?.[0]?.frameId);
    setClip(id);setPlaying(false);
    if(!id)setFrame(1);
    else if(first>=0)setFrame(first+1);
  }
  function apply(operation){
    const data=rows.map(row=>fields.map(field=>row[field]));
    const [updated,message]=applySpriteCanvas(data,target,selection,operation,canvas.current);
    if(updated.data)onEdit(updated.data.map(row=>Object.fromEntries(fields.map((field,i)=>[field,row[i]]))));
    if(operation==="discard")refresh(n=>n+1);
    setNotice(message);
  }
  const [frame,setFrame]=useState(1),[playing,setPlaying]=useState(false),[clip,setClip]=useState("");
  const [shadow,setShadow]=useState(false),[baseline,setBaseline]=useState(true),[onion,setOnion]=useState(false);
  useEffect(()=>{
    const el=canvas.current;
    const message=renderSpritePreview("data:image/png;base64,"+image,rows.map(row=>fields.map(field=>row[field])),frame,
      playing,shadow,mode,bounds,fps,baseline,onion,clip,original || {},gameSize,referenceHeight,gameHeight,feet,{},guide,el);
    setPreviewStatus(message);
    return ()=>{el.spritePreviewRevision++;};
  },[image,rows,frame,playing,shadow,bounds,fps,baseline,onion,clip,original,mode,revision,gameSize,referenceHeight,gameHeight,feet,guide]);
  return <fieldset><legend>프레임 재생 미리보기</legend>
    <canvas ref={canvas} onPointerUp={()=>{if(mode==="머리 기준")onReferenceEdit();}} width="640" height="640" aria-label="크롭과 앵커 미리보기" style={{width:"100%",maxWidth:640,touchAction:"none"}}/>
    <p role="status">{previewStatus}</p>
    <button type="button" onClick={togglePlayback}>{playing?"정지":"재생"}</button>
    <fieldset disabled={playing}><legend>캔버스 편집</legend>
      <label>편집 도구<select value={mode} onChange={e=>setMode(e.target.value)}>
        <option>크롭</option><option>배치 앵커</option><option>머리 기준</option></select></label>
      <label>반영 대상<select value={target} onChange={e=>setTarget(e.target.value)}>
        <option>현재 프레임</option><option>선택 프레임</option><option>전체</option></select></label>
      {target==="선택 프레임" && <label>대상 프레임<select multiple value={selection}
        onChange={e=>setSelection(Array.from(e.target.selectedOptions,option=>option.value))}>
        {rows.map((_,i)=><option key={i} value={i+1}>{i+1}</option>)}</select></label>}
      <button type="button" onClick={()=>apply("apply")}>캔버스 편집 반영</button>
      <button type="button" onClick={()=>apply("undo")}>직전 반영 되돌리기</button>
      <button type="button" onClick={()=>apply("discard")}>드래그 취소</button>
      {notice && <p role="status">{notice}</p>}
    </fieldset>
    <label>정지 프레임 {frame}<input type="range" min="1" max={rows.length} disabled={playing} value={frame}
      onChange={e=>setFrame(Number(e.target.value))}/></label>
    {original?.animation?.clips?.length>0 && <label>검수 동작<select value={clip} onChange={e=>selectClip(e.target.value)}>
      <option value="">전체 시트</option>{original.animation.clips.map(item=><option key={item.clipId} value={item.clipId}>{item.action} · {item.direction}</option>)}</select></label>}
    <details><summary>게임 출력 크기 검수</summary>
      <label><input type="checkbox" checked={gameSize} onChange={e=>setGameSize(e.target.checked)}/>게임 픽셀 크기로 표시</label>
      <label>원본 신체 높이 (px)<input inputMode="decimal" value={referenceHeight} onChange={e=>setReferenceHeight(e.target.value)}/></label>
      <label>게임 출력 신체 높이 (px)<input inputMode="decimal" value={gameHeight} onChange={e=>setGameHeight(e.target.value)}/></label>
      <label><input type="checkbox" checked={guide} onChange={e=>setGuide(e.target.checked)}/>게임 80px 높이 기준</label>
      <label><input type="checkbox" checked={feet} onChange={e=>setFeet(e.target.checked)}/>등록된 양발 중심</label>
    </details>
    <label><input type="checkbox" checked={shadow} onChange={e=>setShadow(e.target.checked)}/>바닥 그림자</label>
    <label><input type="checkbox" checked={baseline} onChange={e=>setBaseline(e.target.checked)}/>앵커 기준선</label>
    <label><input type="checkbox" checked={onion} onChange={e=>setOnion(e.target.checked)}/>이전 프레임 겹쳐보기</label>
  </fieldset>;
}

function BulkEdit({rows,onEdit}){
  const [target,setTarget]=useState("전체"),[range,setRange]=useState(""),[mode,setMode]=useState("크롭");
  const [values,setValues]=useState([0,0,0,0,rows[0].anchorX,rows[0].anchorY]),[notice,setNotice]=useState("");
  const names=["왼쪽 여백","위쪽 여백","오른쪽 여백","아래쪽 여백","공통 앵커 X","공통 앵커 Y"];
  function apply(){
    const [result,message]=editSpriteFrames(rows.map(row=>fields.map(field=>row[field])),target,range,mode,
      ...values.map(value=>value===""?NaN:Number(value)));
    if(result.data)onEdit(result.data.map(row=>Object.fromEntries(fields.map((field,i)=>[field,row[i]]))));
    setNotice(message);
  }
  return <details><summary>프레임 일괄 편집</summary>
    <label>적용 대상<select value={target} onChange={e=>setTarget(e.target.value)}><option>전체</option><option>지정 프레임</option></select></label>
    {target==="지정 프레임" && <label>프레임 번호<input placeholder="1,3-5" value={range} onChange={e=>setRange(e.target.value)}/></label>}
    <label>편집 종류<select value={mode} onChange={e=>setMode(e.target.value)}><option>크롭</option><option>앵커</option></select></label>
    {(mode==="크롭"?[0,1,2,3]:[4,5]).map(i=><label key={i}>{names[i]}<input inputMode="decimal" value={values[i]}
      onChange={e=>setValues(values.map((v,j)=>j===i?e.target.value:v))}/></label>)}
    <button type="button" onClick={apply}>일괄 적용</button>{notice && <p role="status">{notice}</p>}
  </details>;
}

function FrameEditor({image,frames,initialColumns=4,bounds,original,onSaved}){
  const [rows,setRows]=useState(()=>frames.map(({rect,anchor})=>({...rect,anchorX:anchor.x,anchorY:anchor.y})));
  const [columns,setColumns]=useState(initialColumns),[busy,setBusy]=useState(false);
  const [result,setResult]=useState(null),[error,setError]=useState("");
  const [first,setFirst]=useState(1),[last,setLast]=useState(rows.length),[fps,setFps]=useState(6);
  const [review,setReview]=useState(null);
  const canvas=useRef(null);
  function readBodyReference(){
    if(original?.source!=="assets")return null;
    const reference=canvas.current?.spriteEditorState?.bodyReference;
    return reference?{frame:reference.frame,headY:reference.headY}:null;
  }
  function editRows(next){
    setRows(next);
    setReview(null);setResult(null);setError("");
  }
  function update(index,field,value){
    editRows(rows.map((row,i)=>i===index?{...row,[field]:value}:row));
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
        sourceFrames:bounds?bounds.slice(start,end):frames.slice(start,end).map(({rect})=>[rect.x,rect.y,rect.width,rect.height])
      };
      if(event.nativeEvent.submitter?.value==="review"){
        const registered=original.animation?.frames;
        const count=registered?.length || original.layout?.frame_count || original.layout?.columns*original.layout?.rows;
        if(count!==payload.frames.length)throw new Error("원본 갱신은 기존 프레임 수를 유지해야 합니다.");
        const changed=registered?registered.filter(({rect,anchor},i)=>{
          const next=payload.frames[i];
          return ["x","y","width","height"].some(key=>rect[key]!==next[key]) || anchor.x!==next.anchorX || anchor.y!==next.anchorY;
        }).length:count;
        setReview({payload,changed,bodyReference:readBodyReference()});return;
      }
      if(gif)payload.fps=Number(fps);
      const record=await managementCommand("character-animation",gif?"sheet-gif":"sheet-export",payload);
      if(!record.id || (gif?!record.gif:!record.image || !record.coordinates))throw new Error("내보내기 결과를 확인할 수 없습니다.");
      setResult(record);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  async function save(){
    setBusy(true);setError("");
    try{
      const request={path:original.path,metadataSha256:original.metadataSha256,payload:review.payload,confirm:true};
      if(JSON.stringify(review.bodyReference)!==JSON.stringify(readBodyReference())){
        throw new Error("머리 기준이 바뀌었습니다. 원본 갱신 내용을 다시 검토하세요.");
      }
      if(review.bodyReference)request.bodyReference=review.bodyReference;
      if(original.source==="baseline")request.source="baseline";
      const record=await managementCommand("character-animation","sheet-update",request);
      if(!record.id || record.path!==original.path)throw new Error("원본 갱신 결과를 확인할 수 없습니다.");
      onSaved(record);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);setReview(null);}
  }
  return <form onSubmit={exportSheet}><fieldset disabled={busy}><legend>크롭과 앵커 편집</legend>
    <ResultTable table={{title:"등록 프레임 좌표",summary:frames.length+"프레임",columns:["프레임",...labels],
      rows:rows.map((row,i)=>[i+1,...fields.map((field,j)=><input aria-label={(i+1)+"번 "+labels[j]} type="number"
        required step={j<4?1:"any"} value={row[field]} onChange={e=>update(i,field,e.target.value)}/>)])}}/>
    <BulkEdit rows={rows} onEdit={editRows}/>
    <SpritePreview canvas={canvas} onReferenceEdit={()=>setReview(null)} onEdit={editRows} rows={rows} image={image} bounds={bounds} fps={fps} original={original}/>
    <label>출력 열 수<input type="number" min="1" max="128" required value={columns}
      onChange={e=>{setColumns(e.target.value);setReview(null);setResult(null);}}/></label>
    <button>시트와 좌표맵 내보내기</button>
    {original?.metadataSha256 && <button value="review">원본 갱신 검토</button>}
    {review && <section><h3>{original.path}</h3><p>좌표 변경 {review.changed} / {rows.length}프레임 · 출력 {columns}열</p>
      {review.bodyReference && <p>머리 기준 · {review.bodyReference.frame}번 프레임 · Y {review.bodyReference.headY}px</p>}
      <p>{original.source==="baseline"?"베이스라인 이미지·좌표맵·YAML":"등록 이미지·좌표맵·등록부와 잠금 해시"}를 갱신합니다.</p>
      <button type="button" onClick={save}>확인 후 원본 갱신</button>
      <button type="button" onClick={()=>setReview(null)}>취소</button></section>}
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

function GridEditor({detail,size,onSaved}){
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
    {grid && <FrameEditor key={grid.key} frames={grid.frames} image={detail.image} original={detail} onSaved={onSaved}/>}</>;
}

function Sheet({path,source}){
  const [saved,setSaved]=useState(null);
  const [detail,setDetail]=useState(null),[error,setError]=useState("");
  useEffect(()=>{
    let active=true;
    managementCommand("character-animation","sheet-image",{path,source}).then(record=>{
      if(record.path!==path || !record.image)throw new Error("선택한 시트 원본을 확인할 수 없습니다.");
      if(active)setDetail({...record,source});
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[path,source,saved]);
  return <>{saved && <p role="status">원본 갱신 완료 · {saved.path} · 기록 {saved.id}</p>}
    {error?<p role="alert">{error}</p>:detail?<SheetView path={path} detail={detail} onSaved={record=>{
      setDetail(null);setSaved(record);
    }}/>:<p role="status">원본 시트를 불러오는 중…</p>}</>;
}

function AutoCrop({image,size,onApply}){
  const [padding,setPadding]=useState(30),[busy,setBusy]=useState(false);
  const [candidate,setCandidate]=useState(null),[error,setError]=useState("");
  async function detect(event){
    event.preventDefault();setBusy(true);setCandidate(null);setError("");
    try{
      const result=await managementCommand("character-animation","sheet-auto",{image,padding:Number(padding)});
      if(!result.frames?.length || result.sourceFrames?.length!==result.frames.length)throw new Error("검출 결과를 확인할 수 없습니다.");
      setCandidate(result);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <details><summary>자동 크롭</summary><form onSubmit={detect}><fieldset disabled={busy}>
    <label>상하좌우 최소 여백 (px)<input type="number" min="0" max="500" required value={padding}
      onChange={e=>{setPadding(e.target.value);setCandidate(null);setError("");}}/></label>
    <button disabled={!size}>크롭 후보 검출</button></fieldset></form>
    {error && <p role="alert">{error}</p>}
    {candidate && <><svg viewBox={`0 0 ${size.width} ${size.height}`} style={{width:"100%",maxWidth:size.width}} aria-label="크롭 후보 영역">
      <image href={"data:image/png;base64,"+image} width={size.width} height={size.height}/>
      {candidate.frames.map(({x,y,width,height},i)=><g key={i}><rect x={x} y={y} width={width} height={height} fill="none" stroke="red" strokeWidth="2"/>
        <text x={Math.max(0,x)+3} y={Math.max(0,y)+14} fill="red">{i+1}</text></g>)}</svg>
      <p>{candidate.frames.length}개 후보 · 적용하면 현재 프레임 편집을 교체합니다.</p>
      <button onClick={()=>{onApply(candidate);setCandidate(null);}}>검출 결과 적용</button>
      <button onClick={()=>setCandidate(null)}>취소</button></>}
  </details>;
}

function SheetView({path,detail,onSaved}){
  const [size,setSize]=useState(null);
  const [detected,setDetected]=useState(null),[revision,setRevision]=useState(0);
  const frames=detected?.frames || detail.animation?.frames;
  function apply(result){
    const next=result.frames.map(({x,y,width,height,anchorX,anchorY})=>({rect:{x,y,width,height},anchor:{x:anchorX,y:anchorY}}));
    setDetected({frames:next,columns:result.columns,bounds:result.sourceFrames});setRevision(n=>n+1);
  }
  return <section><h2>{path}</h2><img src={"data:image/png;base64,"+detail.image} onLoad={e=>setSize({width:e.target.naturalWidth,height:e.target.naturalHeight})} alt="원본 스프라이트 시트" style={{maxWidth:"100%"}}/>
    {detail.layout && <p>{detail.layout.columns}열 × {detail.layout.rows}행</p>}
    <AutoCrop image={detail.image} size={size} onApply={apply}/>
    {frames?.length>0?<FrameEditor key={revision} frames={frames} image={detail.image} initialColumns={detected?.columns} bounds={detected?.bounds} original={detail} onSaved={onSaved}/>:<GridEditor detail={detail} size={size} onSaved={onSaved}/>}
  </section>;
}

async function readLocalSheet(file){
  if(file.size>8_000_000)throw new Error("PNG 시트는 8MB 이하여야 합니다.");
  const header=new Uint8Array(await file.slice(0,24).arrayBuffer());
  if(header.length!==24 || ![137,80,78,71,13,10,26,10].every((v,i)=>header[i]===v)){
    throw new Error("PNG 시트를 선택하세요.");
  }
  const view=new DataView(header.buffer),width=view.getUint32(16),height=view.getUint32(20);
  if(!width || !height || width*height>16_777_216)throw new Error("1600만 픽셀 이하의 PNG가 필요합니다.");
  const bitmap=await createImageBitmap(file);
  bitmap.close();
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve({image:reader.result.split(",")[1],path:file.name});
    reader.onerror=()=>reject(new Error("PNG 시트를 읽을 수 없습니다."));
    reader.readAsDataURL(file);
  });
}

function LocalSheet(){
  const [file,setFile]=useState(null),[detail,setDetail]=useState(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState(""),[revision,setRevision]=useState(0);
  async function load(){
    setBusy(true);setError("");
    try{
      const result=await readLocalSheet(file);
      setDetail(result);setRevision(n=>n+1);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  return <details><summary>로컬 PNG 편집</summary>
    <fieldset disabled={busy}><label>시트 PNG<input type="file" accept="image/png" onChange={e=>{
      setFile(e.target.files[0] || null);setError("");
    }}/></label>
    <button disabled={!file} onClick={load}>{detail?"편집 중인 로컬 시트 교체":"로컬 시트 열기"}</button></fieldset>
    {error && <p role="alert">{error}</p>}
    {detail && <SheetView key={revision} path={detail.path} detail={detail}/>}
  </details>;
}

function linkedSheet(){
  const params=new URLSearchParams(location.search);
  const path=params.get("sprite_path") || "",action=params.get("action") || "";
  const source=params.get("sprite_source") ?? "assets";
  if((path || action) && !["assets","baseline"].includes(source))return {error:"지원하지 않는 링크 원본입니다."};
  if(path)return {source,path};
  if(!action)return {};
  if(!action.startsWith("asset:") || action.length===6)return {error:"지원하지 않는 애니메이션 링크입니다."};
  return {source:"assets",animation:action.slice(6)};
}

export default function SpriteSheetEditor(){
  const [link]=useState(linkedSheet);
  const [source,setSource]=useState(link.source || "assets"),[query,setQuery]=useState(link.animation || "");
  const [request,setRequest]=useState(link.animation?{source:"assets",query:link.animation,linked:true}:null);
  const [items,setItems]=useState(null),[selected,select]=useState(link.path || "");
  const [error,setError]=useState(link.error || "");
  useEffect(()=>{
    if(!request)return;
    let active=true;
    managementCommand("character-animation","sheet-search",{source:request.source,query:request.query}).then(result=>{
      if(!active)return;
      setItems(result.items);
      if(request.linked){
        const matches=result.items.filter(item=>item.animationIds?.includes(request.query));
        if(matches.length===1)select(matches[0].path);
        else setError("동작 ID에 연결된 시트가 없거나 여러 개입니다. 검색 결과에서 원본을 선택하세요.");
      }
    }).catch(problem=>{if(active)setError(problem.message);});
    return ()=>{active=false;};
  },[request]);
  function search(nextSource){
    setItems(null);setError("");select("");setRequest({source:nextSource,query});
  }
  return <article><h1>스프라이트 시트 편집기</h1><LocalSheet/>
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
