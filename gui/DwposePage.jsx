import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ActionButton from "./ActionButton.jsx";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import MockProgress,{jobsPath} from "./MockProgress.jsx";
import GeneratorJobResult from "./GeneratorJobResult.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import React, {useRef,useState} from "react";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import {managementCommand} from "./managementCommand.js";

async function pngData(file) {
  const signature=new Uint8Array(await file.slice(0,8).arrayBuffer());
  if(signature.join(",")!=="137,80,78,71,13,10,26,10")throw new Error("PNG 파일을 선택하세요.");
  const image=await createImageBitmap(file);
  const valid=image.width===832 && image.height===480;
  image.close();
  if(!valid)throw new Error("832×480 PNG가 필요합니다.");
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(reader.result.split(",")[1]);
    reader.onerror=()=>reject(new Error("파일을 읽을 수 없습니다."));
    reader.readAsDataURL(file);
  });
}

export default function DwposePage({mock=false,embedded=false}={}) {
  const query=new URLSearchParams(location.search);
  const [file,setFile]=useState(null),[hands,setHands]=useState(false),[face,setFace]=useState(false);
  const [pending,setPending]=useState(null),[busy,setBusy]=useState(false);
  const [job,setJob]=useState(embedded ? "" : query.get("job") || ""),[notice,setNotice]=useState("");
  const [historyRevision,setHistoryRevision]=useState(0);
  function cleaned(message){
    setJob("");setNotice(message);setHistoryRevision(value=>value+1);
  }
  const sending=useRef(false);
  async function readJob(id){
    const response=await fetch("/management/assistant/dwpose-input/"+encodeURIComponent(id),{cache:"no-store"});
    if(!response.ok)throw new Error("저장된 DWPose 입력을 불러올 수 없습니다.");
    const blob=await response.blob();
    const savedFile=new File([blob],id+"-reference.png",{type:"image/png"});
    return {id,file:savedFile,request:{
      pose_include_hands:response.headers.get("X-Pose-Hands")==="true",
      pose_include_face:response.headers.get("X-Pose-Face")==="true",
    }};
  }
  function restore(request,record){
    setFile(record.file);setHands(request.pose_include_hands);setFace(request.pose_include_face);
    setJob(record.id);setNotice("저장된 PNG와 포즈 옵션을 불러왔습니다.");
  }
  async function review(){
    setBusy(true);setNotice("");
    try {
      setPending({action:"generate",images:[await pngData(file)],pose_include_hands:hands,pose_include_face:face});
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  async function submit(){
    if(!pending || sending.current)return;
    sending.current=true;setBusy(true);
    try {
      let result;
      if(mock){
        const response=await fetch(jobsPath+"?scope=dwpose",{method:"POST"});
        if(!response.ok)throw new Error("모의 작업 등록 실패");
        result=await response.json();
      }else result=await managementCommand("dwpose","generate",pending);
      if(!result.id)throw new Error("작업 ID를 확인할 수 없습니다.");
      setJob(result.id);setNotice(mock?"격리 모의 작업을 등록했습니다.":"공용 GPU 대기열에 등록했습니다.");
    }catch(problem){setNotice(problem.message+" · 이력에서 접수 여부를 확인하세요.");}
    finally{setPending(null);sending.current=false;setBusy(false);}
  }
  return <article>
    <a href={"/management/assistant/"+(query.has("session")?"?"+new URLSearchParams({session:query.get("session")}):"")}>헤르메스 대화</a>
    <h1>DWPose 이미지 추출</h1>
    {mock ? <p>격리 모의 검증 · 메모리에서 작업 상태를 확인합니다.</p> : <><ModelReadiness service="dwpose"/><GeneratorChangelog generator="dwpose-generator"/></>}
    <fieldset disabled={busy || Boolean(pending)}>
      <ReferenceImageInput label="입력 PNG · 832×480" accept="image/png" source={file} validate={pngData} disabled={busy || Boolean(pending)} onChange={setFile}/>
      {file && <p>선택된 입력 · {file.name}</p>}
      {!mock && <GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id) cleaned(message); else setNotice(message);}} key={historyRevision} service="dwpose" readJob={readJob} restore={restore} inspectResult={record=>setJob(record.id)}/>}
      <label><input type="checkbox" checked={hands} onChange={event=>setHands(event.target.checked)}/>손 상세 표시</label>
      <label><input type="checkbox" checked={face} onChange={event=>setFace(event.target.checked)}/>얼굴 상세 표시</label>
      <ActionButton reasons={[!file && "입력 PNG를 선택하세요."]} onClick={review}>생성 요청 검토</ActionButton>
    </fieldset>
    {pending && <section>{!mock && <GpuQueueSummary/>}<p>{file.name} · 손 상세 {hands?"포함":"제외"} · 얼굴 상세 {face?"포함":"제외"}</p>
      <GenerationReviewActions busy={busy} onCancel={()=>setPending(null)} onConfirm={submit}/>
    </section>}
    {notice && <p role="status">{notice}</p>}
    {mock ? <MockProgress key={job} scope="dwpose" initialJob={job}/> : <GeneratorJobResult selectionControls job={job} service="dwpose" controls={false} onDeleted={cleaned}/>}
  </article>;
}
