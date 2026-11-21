import BillboardCrop from "./BillboardCrop.jsx";
import React,{useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ResultTable from "./ResultTable.jsx";

const labels={anchorX:"앵커 X",anchorY:"앵커 Y",displayHeight:"표시 높이",groundFootprintColumns:"점유 열",groundFootprintRows:"점유 행",
  shadowOffsetColumn:"그림자 열 이동",shadowOffsetRow:"그림자 행 이동",shadowScaleX:"그림자 가로 배율",shadowScaleY:"그림자 세로 배율",
  billboardPlacementAnchor:"배치 기준",billboardBlocksMovement:"통행 차단"};

export default function BillboardProperties({texture,onCrop}){
  const [source,setSource]=useState(null),[edits,setEdits]=useState({}),[review,setReview]=useState(null);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  async function load(){
    setBusy(true);setNotice("");setReview(null);
    try{
      const result=await managementCommand("hermes-agent","hermes-billboard-load",{texture});
      if(result.texture!==texture || !result.properties || !result.revision)throw new Error("선택한 에셋 속성을 확인할 수 없습니다.");
      setSource(result);setEdits({});
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  function edit(key,value){
    setEdits({...edits,[key]:value});setReview(null);setNotice("");
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
      setReview(null);setSource(null);setEdits({});setNotice("공용 속성 저장 완료 · 접수 "+review.id);
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  const properties=source?{...source.properties,...edits}:{};
  const automaticPlacement=source?.initial || ["tile-intersection","tile-bottom-center"].includes(properties.billboardAnchorMode);
  return <section><button disabled={busy} onClick={load}>공용 속성 불러오기</button>
    {source && <form onSubmit={preview}><fieldset disabled={busy}><legend>빌보드 공용 속성</legend>
      {source.initial && <p>최초 설정 초안 · 기본 점유 1×1, 표시 높이 128px입니다. 원본을 확인한 뒤 검토하세요.</p>}
      {Object.keys(labels).filter(key=>!key.startsWith("billboard")).map(key=><label key={key}>{labels[key]}
        <input type="number" step="any" required={key in edits} value={properties[key] ?? ""} onChange={e=>edit(key,e.target.value)}/></label>)}
      <label>배치 기준<select disabled={automaticPlacement} value={automaticPlacement?(Number(properties.anchorY)<0.5?"top":"bottom"):(properties.billboardPlacementAnchor ?? "")} onChange={e=>edit("billboardPlacementAnchor",e.target.value)}>
        <option value="" disabled>미지정</option><option value="top">위쪽</option><option value="bottom">아래쪽</option></select></label>
      <label><input type="checkbox" checked={properties.billboardBlocksMovement ?? false} onChange={e=>edit("billboardBlocksMovement",e.target.checked)}/>통행 차단</label>
      <button>변경 검토</button>
      {review && <><ResultTable table={{title:"공용 속성 변경",summary:review.result.note,columns:["속성","기존","변경 후"],
        rows:Object.entries(review.result.changes[0].after).filter(([key,v])=>v!==review.result.changes[0].before[key])
          .map(([key,v])=>[labels[key] || key,String(review.result.changes[0].before[key] ?? ""),String(v)])}}/>
        <p>영향 맵 · {review.result.maps.join(", ") || "없음"}</p>
        {review.result.map_warnings.map((w,i)=><p key={i}>{w.map} · {w.message}</p>)}
        <button type="button" onClick={save}>검토한 속성 저장</button><button type="button" onClick={()=>setReview(null)}>취소</button></>}
    </fieldset></form>}
    {source && !source.initial && !Object.keys(edits).length && <BillboardCrop key={source.revision} source={source} busy={busy} setBusy={setBusy}
      onSaved={()=>{setSource(null);setReview(null);setNotice("원본 크롭 저장 완료");onCrop();}}/>}
    {notice && <p role="status">{notice}</p>}
  </section>;
}
