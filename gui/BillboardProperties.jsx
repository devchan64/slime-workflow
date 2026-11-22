import BillboardGroundPreview from "./BillboardGroundPreview.jsx";
import BillboardCrop from "./BillboardCrop.jsx";
import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";
import {billboardSaveNotice} from "./billboardSaveNotice.mjs";

export const billboardPropertyLabels={anchorX:"앵커 X",anchorY:"앵커 Y",displayHeight:"표시 높이",groundFootprintColumns:"점유 열",groundFootprintRows:"점유 행",
  shadowOffsetColumn:"그림자 열 이동",shadowOffsetRow:"그림자 행 이동",shadowScaleX:"그림자 가로 배율",shadowScaleY:"그림자 세로 배율",
  billboardPlacementAnchor:"배치 기준",billboardBlocksMovement:"통행 차단"};
const labels=billboardPropertyLabels;

export function BillboardReviewSummary({result}){
  const change=result.changes[0];
  return <><p>에셋: {change.texture}</p><ResultTable table={{title:"공용 속성 변경",summary:result.note,columns:["속성","기존","변경 후"],
    rows:Object.entries(change.after).filter(([key,value])=>value!==change.before[key])
      .map(([key,value])=>[labels[key] || key,String(change.before[key] ?? ""),String(value)])}}/>
    <p>영향 맵 · {result.maps.join(", ") || "없음"}</p>
    {result.map_warnings.map((warning,index)=><p key={index}>{warning.map} · {warning.message}</p>)}
  </>;
}

export default function BillboardProperties({texture,onCrop,onDirtyChange=()=>{}}){
  const [source,setSource]=useState(null),[edits,setEdits]=useState({}),[review,setReview]=useState(null);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  async function load(){
    setBusy(true);setNotice("");setReview(null);
    try{
      const result=await managementCommand("hermes-agent","hermes-billboard-load",{texture});
      if(result.texture!==texture || !result.properties || !result.revision)throw new Error("선택한 에셋 속성을 확인할 수 없습니다.");
      setSource(result);setEdits({});onDirtyChange(false);
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  function edit(key,value){
    setEdits({...edits,[key]:value});onDirtyChange(true);setReview(null);setNotice("");
  }
  async function preview(event){
    event.preventDefault();setBusy(true);setNotice("");setReview(null);
    try{
      const values=source.initial?{...source.properties}:{};
      for(const [key,raw] of Object.entries(edits)){
        const value=key==="billboardPlacementAnchor" || key==="billboardBlocksMovement"?raw:Number(raw);
        if(value!==source.properties[key])values[key]=value;
      }
      if(!Object.keys(values).length)throw new Error("변경할 속성을 입력하세요.");
      const draft={revision:source.revision,changes:[{texture,values}]};
      const result=await managementCommand("hermes-agent","hermes-billboard-preview",{draft});
      if(!result.token || !result.review_sha256 || result.changes?.[0]?.texture!==texture)throw new Error("검토 결과가 선택한 에셋과 다릅니다.");
      setReview({result,draft,id:crypto.randomUUID().replaceAll("-","")});
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  async function save(){
    setBusy(true);setNotice("");
    try{
      const record=await managementCommand("hermes-agent","hermes-billboard-save",{request_id:review.id,draft:review.draft,
        token:review.result.token,review_sha256:review.result.review_sha256});
      if(record.state!=="completed" || !record.saved)throw new Error("저장 결과 확인 필요 · 접수 "+review.id);
      setReview(null);setSource(null);setEdits({});onDirtyChange(false);setNotice(billboardSaveNotice(record,review.id));
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  const hasEdits=Object.keys(edits).length>0;
  const properties=source?{...source.properties,...edits}:{};
  const automaticPlacement=source?.initial || ["tile-intersection","tile-bottom-center"].includes(properties.billboardAnchorMode);
  return <section><button type="button" disabled={busy || hasEdits} onClick={load}>{source?"공용 속성 다시 불러오기":"공용 속성 불러오기"}</button>
    {hasEdits && <p role="status">변경 사항이 있습니다. 다시 불러오려면 편집을 취소하거나 저장하세요. <button type="button" disabled={busy} onClick={()=>{setEdits({});onDirtyChange(false);setReview(null);setNotice("");}}>편집 취소</button></p>}
    {source && <form className="billboard-properties-form" onSubmit={preview}><fieldset disabled={busy}><legend>빌보드 공용 속성</legend>
      {source.initial && <p>최초 설정 초안 · 기본 점유 1×1, 표시 높이 128px입니다. 원본을 확인한 뒤 검토하세요.</p>}
      <div className="billboard-properties-grid">{Object.keys(labels).filter(key=>!key.startsWith("billboard")).map(key=><label key={key}>{labels[key]}
        <input type="number" step="any" required={key in edits} value={properties[key] ?? ""} onChange={e=>edit(key,e.target.value)}/></label>)}
      <label>배치 기준<select disabled={automaticPlacement} value={automaticPlacement?(Number(properties.anchorY)<0.5?"top":"bottom"):(properties.billboardPlacementAnchor ?? "")} onChange={e=>edit("billboardPlacementAnchor",e.target.value)}>
        <option value="" disabled>미지정</option><option value="top">위쪽</option><option value="bottom">아래쪽</option></select></label>
      <label className="billboard-checkbox"><input type="checkbox" checked={properties.billboardBlocksMovement ?? false} onChange={e=>edit("billboardBlocksMovement",e.target.checked)}/>통행 차단</label></div>
      <BillboardGroundPreview source={source} edits={edits}/>
      <button>변경 검토</button>
      {review && <><BillboardReviewSummary result={review.result}/>
        <button type="button" onClick={save}>검토한 속성 저장</button><button type="button" onClick={()=>setReview(null)}>취소</button></>}
    </fieldset></form>}
    {source && !source.initial && !hasEdits && <BillboardCrop key={source.revision} source={source} busy={busy} setBusy={setBusy}
      onSaved={()=>{setSource(null);setReview(null);setNotice("원본 크롭 저장 완료");onCrop();}}/>}
    {notice && <p role="status">{notice}</p>}
  </section>;
}
