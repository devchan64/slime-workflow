import React,{useEffect,useState} from "react";
import readReference from "./readReference.js";
import KimodoPromptExamples from "./KimodoPromptExamples.jsx";
import {managementCommand} from "./managementCommand.js";

export default function KimodoGeneration({session}){
  const [directions,setDirections]=useState({});
  const [references,setReferences]=useState([]);
  const [bundle,setBundle]=useState(null),[calibration,setCalibration]=useState(null),[hip,setHip]=useState(false);
  const [angles,setAngles]=useState("");
  const [segments,setSegments]=useState("");
  const key="kimodo-generation-receipt-"+session;
  const [inputs,setInputs]=useState(null),[review,setReview]=useState(null),[busy,setBusy]=useState(false);
  const [receipt,setReceipt]=useState(()=>sessionStorage.getItem(key) || ""),[notice,setNotice]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    fetch("/management/assistant/kimodo-generation-template",{signal:controller.signal}).then(async response=>{
      if(!response.ok)throw new Error("생성 기본값을 조회할 수 없습니다.");
      const defaults=await response.json();
      if(!controller.signal.aborted){setInputs(defaults.inputs);setDirections(defaults.directions);}
    }).catch(error=>{if(!controller.signal.aborted)setNotice(error.message);});
    return ()=>controller.abort();
  },[]);
  function edit(field,value){
    setInputs(previous=>({...previous,[field]:value}));setReview(null);
  }
  async function perform(action){
    setBusy(true);setNotice("");
    try{await action();}catch(error){setNotice(error.message);}finally{setBusy(false);}
  }
  async function inspect(){
    setReview(null);
    const request={...inputs,frames:Number(inputs.frames),steps:Number(inputs.steps),seed:Number(inputs.seed),
      guidance_scale:Number(inputs.guidance_scale),openpose_scale_percent:Number(inputs.openpose_scale_percent)};
    if(references.length){
      if(references.length>8)throw new Error("참조 이미지는 최대 8장입니다.");
      if(references.some(file=>file.size>3000000))throw new Error("참조 PNG는 파일당 3 MB까지 첨부할 수 있습니다.");
      request.proportion_images=await Promise.all(references.map(readReference));
    }
    if(bundle){
      if(bundle.size>2*1024*1024)throw new Error("검수 골격 묶음은 2 MiB 이하여야 합니다.");
      request.proportion_reviewed_multiview=JSON.parse(await bundle.text());
      if(hip)request.proportion_projected_hip=true;
      if(calibration){
        if(calibration.size>65536)throw new Error("얼굴 앵커 교정 파일은 64 KiB 이하여야 합니다.");
        request.proportion_face_anchor_calibration=JSON.parse(await calibration.text());
      }
    }
    if(angles.trim()){
      const values=angles.trim().split(/\s+/).map(Number);
      if(values.some(value=>!Number.isFinite(value)))throw new Error("카메라 각도는 공백으로 구분한 숫자로 입력하세요.");
      request.proportion_multiview_angles=values;
    }
    if(segments.trim()){
      const counts=segments.trim().split(/\s+/);
      if(counts.some(value=>!/^\d+$/.test(value)))throw new Error("구간 프레임 수는 공백으로 구분한 정수로 입력하세요.");
      request.segment_frames=counts.map(Number);
    }
    const response=await fetch("/management/assistant/kimodo-generation-review",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify(request)});
    const result=await response.json();
    if(!response.ok)throw new Error(result.detail || "생성 입력을 확인하세요.");
    const model=await fetch("/management/assistant/model-readiness/kimodo",{cache:"no-store"});
    if(!model.ok)throw new Error("모델 상태를 확인할 수 없습니다.");
    const status=await model.json();
    if(!(status.generation_ready ?? status.ready))throw new Error(status.message || "모델 준비가 필요합니다.");
    setReview(result.request);
  }
  async function submit(){
    const id=crypto.randomUUID().replaceAll("-","");
    sessionStorage.setItem(key,id);setReceipt(id);setReview(null);
    const result=await managementCommand("hermes-agent","hermes-delegate-kimodo",{request_id:id,request:review});
    setNotice(result.state==="accepted"?"GPU 대기열에 등록했습니다. 작업 "+result.job_id:"접수 상태를 조회하세요.");
  }
  return <section aria-label="Kimodo 모션 생성"><h2>모션 생성</h2>
    {inputs && <form onSubmit={e=>{e.preventDefault();perform(inspect);}}><fieldset disabled={busy}>
      <label>동작 설명 <textarea required maxLength={2000} value={inputs.prompt} onChange={e=>edit("prompt",e.target.value)}/></label>
      <KimodoPromptExamples apply={prompt=>edit("prompt",prompt)}/>
      {[["frames","프레임 수",30,300],["steps","생성 단계",2,100],["seed","시드",0,2147483647]].map(([field,label,min,max])=>
        <label key={field}>{label} <input type="number" required min={min} max={max} value={inputs[field]} onChange={e=>edit(field,e.target.value)}/></label>)}
      <label>신체 비율 참조 PNG (최대 8장) <input type="file" accept="image/png" multiple
        onChange={e=>{setReferences(Array.from(e.target.files));setReview(null);}}/></label>
      <details><summary>다중 시점 신체 비율</summary>
        <label>검출 관측 순서의 카메라 각도 8개 (도) <input value={angles} placeholder="45 0 135 90 225 315 180 270"
          onChange={e=>{setAngles(e.target.value);setReview(null);}}/></label>
        <p>참조 이미지에서 검출된 관측 순서대로 각도를 입력하세요. 각도와 검수 골격을 모두 비우면 2D 보정을 사용합니다.</p>
        <label>검수 3D 골격 묶음 JSON <input type="file" accept=".json,application/json"
          onChange={e=>{setBundle(e.target.files[0] || null);if(!e.target.files.length){setCalibration(null);setHip(false);}setReview(null);}}/></label>
        {bundle && <fieldset><legend>검수 골격 적용</legend>
          <label><input type="checkbox" checked={hip} onChange={e=>{setHip(e.target.checked);setReview(null);}}/>3D 투영 골반 적용</label>
          <label>얼굴 앵커 교정 JSON <input type="file" accept=".json,application/json"
            onChange={e=>{setCalibration(e.target.files[0] || null);setReview(null);}}/></label>
        </fieldset>}
      </details>
      <details><summary>모션 및 포즈 출력 설정</summary>
        <label>구간별 프레임 수 <input value={segments} placeholder="예: 45 45"
          onChange={e=>{setSegments(e.target.value);setReview(null);}}/></label>
        <p>순차 생성은 동작 설명을 줄마다 하나씩 입력하세요. 각 구간은 16프레임 이상이며 합계는 전체 프레임 수와 같아야 합니다.</p>
        <fieldset><legend>카메라 방향</legend>{Object.entries(directions).map(([id,direction])=>
          <label key={id}><input type="checkbox" checked={inputs.directions.includes(id)}
            onChange={e=>edit("directions",e.target.checked?[...inputs.directions,id]:inputs.directions.filter(item=>item!==id))}/>
            {direction.label} ({direction.angle}°)</label>)}</fieldset>
        <label>카메라 고도 <select value={inputs.camera_elevation_degrees} onChange={e=>edit("camera_elevation_degrees",Number(e.target.value))}>
          {[0,15,30].map(value=><option key={value} value={value}>{value}°</option>)}</select></label>
        <label>텍스트 CFG <input type="number" required min="0" max="10" step="any" value={inputs.guidance_scale}
          onChange={e=>edit("guidance_scale",e.target.value)}/></label>
        <label>OpenPose 출력 크기 (%) <input type="number" required min="10" max="100" step="0.5" value={inputs.openpose_scale_percent}
          onChange={e=>edit("openpose_scale_percent",e.target.value)}/></label>
        {[["post_processing","공식 후처리"],["remove_horizontal_motion","수평 이동 제거"],["pose_include_hands","손 포즈 포함"],
          ["pose_include_face","얼굴 포즈 포함"]].map(([field,label])=>
          <label key={field}><input type="checkbox" checked={inputs[field]} onChange={e=>edit(field,e.target.checked)}/>{label}</label>)}
      </details>
      <button>생성 요청 검토</button>
    </fieldset></form>}
    {review && <section><pre>{JSON.stringify(review,(key,value)=>key==="proportion_images"?references.map(file=>file.name):key==="proportion_reviewed_multiview"?bundle.name:key==="proportion_face_anchor_calibration"?calibration.name:value,2)}</pre>
      <button disabled={busy} onClick={()=>perform(submit)}>GPU 대기열에 등록</button>
      <button disabled={busy} onClick={()=>setReview(null)}>취소</button></section>}
    {receipt && <p>최근 접수 ID <code>{receipt}</code> <button disabled={busy} onClick={()=>perform(async()=>{
      const result=await managementCommand("hermes-agent","hermes-delegation-status",{request_id:receipt});
      setNotice([result.state,result.job_id].filter(Boolean).join(" · "));
    })}>접수 상태 조회</button></p>}
    {notice && <p role="status">{notice}</p>}
  </section>;
}
