import GenerationReviewActions from "./GenerationReviewActions.jsx";
import ActionButton from "./ActionButton.jsx";
import React,{useEffect,useRef,useState} from "react";
import {referencePng,videoData} from "./videoInputs.js";
import GeneratorHistory from "./GeneratorHistory.jsx";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import ModelReadiness from "./ModelReadiness.jsx";

import GpuQueueSummary from "./GpuQueueSummary.jsx";
import {FunControlFields,FunControlResult} from "./FunControlSchema.jsx";
import {managementCommand} from "./managementCommand.js";

export default function FunControlPage({embedded=false,session="",restoreFormId="",seedProposal=null,onSaved=()=>{}}){
  const [template,setTemplate]=useState(null),[selected,select]=useState("");
  const [request,setRequest]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [pending,setPending]=useState(null),[job,setJob]=useState(new URLSearchParams(location.search).get("job") || "");
  const [videoInfo,setVideoInfo]=useState(null);
  const [sourceSeed,setSourceSeed]=useState(null);
  const [sourceJob,setSourceJob]=useState("");
  const [historyRevision,refreshHistory]=useState(0);
  const [notice,setNotice]=useState("");
  const service="wan22-fun-control";
  async function readJob(id){
    const response=await fetch("/management/assistant/fun-input/"+encodeURIComponent(id),{cache:"no-store"});
    if(!response.ok)throw new Error("이 작업의 입력 사본을 복원할 수 없습니다.");
    const record=await response.json();
    const {images,pose_video,...settings}=record.request;
    return {...record,request:settings,attachments:{images,pose_video}};
  }
  function restore(settings,record){
    setRequest({...settings,...record.attachments});setVideoInfo(record.video);setSourceSeed(Number(settings.seed));setSourceJob(record.id);setJob(record.id);
    setNotice(record.id+" 입력을 복원했습니다.");refreshHistory(n=>n+1);
  }
  function cleaned(message){setJob("");setNotice(message);refreshHistory(n=>n+1);}
  const sending=useRef(false);
  const saveAttempt=useRef(null);
  async function saveForm(value=request){
    value={...value,...Object.fromEntries(["frames","steps","seed","flow_shift","guidance_scale","switch_ratio"].map(key=>[key,Number(value[key])]))};
    const serialized=JSON.stringify({request:value,video_info:videoInfo});
    if(!saveAttempt.current || saveAttempt.current.serialized!==serialized)
      saveAttempt.current={id:crypto.randomUUID().replaceAll("-",""),serialized};
    const form_id=saveAttempt.current.id;
    await managementCommand("hermes-agent","hermes-video-form-save",{session_id:session,form_id,request:value,video_info:videoInfo});
    onSaved(); return form_id;
  }
  async function saveDraft(){
    setBusy(true);setError("");
    try{await saveForm();setNotice("생성 폼을 대화에 저장했습니다.");}catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  async function submit(){
    if(!pending || sending.current)return;
    sending.current=true;setBusy(true);setError("");
    try{
      const form_id=embedded ? await saveForm(pending) : null;
      const result=embedded ? await managementCommand("hermes-agent","hermes-video-form-submit",{session_id:session,form_id}) : await managementCommand("wan22-fun-control","generate",pending);
      if(embedded && result.state!=="accepted")throw new Error("접수 결과 확인 필요 · 저장된 메시지에서 상태를 확인하세요.");
      const jobId=embedded ? result.job_id : result.id;
      if(!jobId)throw new Error("작업 ID를 확인할 수 없습니다.");
      setJob(jobId);onSaved();
    }catch(problem){setError(problem.message+" · 다시 접수하기 전에 이력을 확인하세요.");}
    finally{sending.current=false;setPending(null);setBusy(false);}
  }
  useEffect(()=>{
    const controller=new AbortController();
    fetch("/management/assistant/fun-template",{signal:controller.signal}).then(async response=>{
      if(!response.ok)throw new Error("예제 목록 조회 실패");
      const data=await response.json();
      if(!controller.signal.aborted){setTemplate(data);setRequest({...data.defaults,action:"generate",control_type:"pose",width:832,height:480,images:[],pose_video:"",prompt:"",negative_prompt:""});select(data.examples[0]?.id || "");}
    }).catch(problem=>{if(!controller.signal.aborted)setError(problem.message);});
    return ()=>controller.abort();
  },[]);
  useEffect(()=>{
    if(!embedded || !session || !restoreFormId || !template)return;
    let active=true;setBusy(true);setError("");
    managementCommand("hermes-agent","hermes-video-form-read",{session_id:session,form_id:restoreFormId}).then(record=>{
      if(active){setRequest(record.request);setVideoInfo(record.video_info);setSourceSeed(null);setSourceJob("");setJob("");setNotice("대화에 저장된 폼을 불러왔습니다. 변경하면 새 메시지로 저장됩니다.");saveAttempt.current={id:restoreFormId,serialized:JSON.stringify({request:record.request,video_info:record.video_info})};}
    }).catch(problem=>{if(active)setError(problem.message);}).finally(()=>{if(active)setBusy(false);});
    return ()=>{active=false;};
  },[embedded,session,restoreFormId,template]);
  useEffect(()=>{
    if(!embedded || !seedProposal || !template)return;
    const controller=new AbortController();setBusy(true);setError("");
    (async()=>{
      const response=await fetch("/management/assistant/fun-input/"+encodeURIComponent(seedProposal.job_id),{signal:controller.signal,cache:"no-store"});
      if(!response.ok)throw new Error("원본 작업 입력을 확인할 수 없습니다. 생성 이력에서 입력을 직접 선택하세요.");
      const record=await response.json();
      if(record.id!==seedProposal.job_id || !record.request || !Number.isInteger(record.request.seed) || record.request.seed<0 || record.request.seed>2147483647)
        throw new Error("원본 작업의 입력이나 시드를 확인할 수 없습니다.");
      let next=seedProposal.reuse ? record.request.seed : seedProposal.seed;
      if(next==null){next=crypto.getRandomValues(new Uint32Array(1))[0] & 0x7fffffff;if(next===record.request.seed)next=(next+1)%2147483648;}
      if(!Number.isInteger(next) || next<0 || next>2147483647)throw new Error("제안한 시드가 허용 범위를 벗어났습니다.");
      if(!controller.signal.aborted){setRequest({...record.request,seed:next});setVideoInfo(record.video);setSourceSeed(record.request.seed);setSourceJob(record.id);setJob("");saveAttempt.current=null;
        setNotice("원본 "+record.id+"의 입력을 불러왔습니다. "+(seedProposal.reuse ? "입력을 확인하세요." : next===record.request.seed ? "원본과 같은 시드입니다. 변경 후 검토하세요." : "입력과 새 시드를 확인하세요."));}
    })().catch(problem=>{if(!controller.signal.aborted)setError(problem.message);}).finally(()=>{if(!controller.signal.aborted)setBusy(false);});
    return ()=>controller.abort();
  },[embedded,seedProposal,template]);
  async function attach(file,field){
    if(!file)return;
    setBusy(true);setError("");
    try{
      const value=field==="images"?[await referencePng(file)]:await videoData(file);
      if(field==="pose_video"){
        const response=await fetch("/management/assistant/fun-video-info",{method:"POST",body:file});
        const info=await response.json();
        if(!response.ok)throw new Error(info.summary || "포즈 영상을 확인할 수 없습니다.");
        setVideoInfo(info);
      }
      setRequest(current=>({...current,[field]:value}));
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  async function load(restore=false){
    setBusy(true);setError("");
    try{
      const id=restore?job:selected;
      const response=await fetch("/management/assistant/"+(restore?"fun-input/":"fun-example/")+encodeURIComponent(id));
      if(!response.ok)throw new Error(restore?"이 작업의 입력 사본을 복원할 수 없습니다.":"예제 첨부 파일을 불러올 수 없습니다.");
      const example=await response.json();
      if(example.id!==id)throw new Error("선택한 예제와 응답이 일치하지 않습니다.");
      setVideoInfo(example.video);setSourceSeed(restore ? Number(example.request.seed) : null);setSourceJob(restore ? example.id : "");
      setRequest(example.request);
    }catch(problem){setError(problem.message);}
    finally{setBusy(false);}
  }
  const frameLimit=videoInfo?.maximum_frames ?? template?.maximum_frames;
  const settings=[
    ["frames","프레임 수",5,frameLimit,4],
    ["steps","스텝",2,100,1],
    ["seed","시드",0,template?.maximum_seed,1],
    ["flow_shift","Flow shift",0.1,20,"any"],
    ["guidance_scale","Guidance scale",1,10,"any"],
    ["switch_ratio","모델 전환 비율",0.1,0.9,"any"],
  ];
  function review(event){
    event.preventDefault();
    const values=Object.fromEntries(settings.map(([key])=>[key,Number(request[key])]));
    setPending({...request,...values});
  }
  return <article className={"fun-control-page"+(embedded?" fun-embedded":"")}>{!embedded && <a href={"/management/frame/hermes-agent/"+(new URLSearchParams(location.search).get("session")?"?"+new URLSearchParams({session:new URLSearchParams(location.search).get("session")}):"")}>헤르메스 대화로 돌아가기</a>}<><h1>Wan Fun Control 영상 생성</h1><GeneratorChangelog generator="wan22-fun-control-generator"/><ModelReadiness service={service}/></>
    <fieldset className="fun-source" disabled={busy || !!pending || !template}><legend>원본 작업</legend>
      <p>{sourceJob ? "불러온 작업 · "+sourceJob : "선택된 원본 작업이 없습니다."}</p>
      <GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id) cleaned(message); else setNotice(message);}} key={historyRevision} service={service} readJob={readJob} restore={restore} openResult={setJob}/>
      {job && <button disabled={!template} onClick={()=>load(true)}>작업 {job} 입력으로 교체</button>}
      <details><summary>제작 예제 사용</summary><label>예제 선택<select value={selected} onChange={event=>select(event.target.value)}>
        {template?.examples.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        <button disabled={!selected} onClick={()=>load()}>선택한 예제로 입력 교체</button></details>
    </fieldset>
    {error && <p role="alert">{error}</p>}
    {request && <form onSubmit={review} onInvalid={event=>{const details=event.target.closest("details");if(details)details.open=true;}}><fieldset disabled={busy || !!pending}><legend>생성 입력</legend>
      <FunControlFields request={request} setRequest={setRequest} attach={attach} videoInfo={videoInfo} frameLimit={frameLimit} template={template} sourceSeed={sourceSeed} busy={busy || !!pending}/>
      {embedded && <button type="button" onClick={saveDraft}>폼을 대화에 저장</button>}
      <ActionButton type="submit" reasons={[
        !request.prompt.trim() && "동작 프롬프트를 입력하세요.",
        !request.images[0] && "외형 참조 이미지를 선택하세요.",
        !request.pose_video && "포즈 영상을 선택하세요."
      ]}>생성 요청 검토</ActionButton>
    </fieldset></form>}
    {pending && <section aria-label="생성 요청 확인"><GpuQueueSummary/>
      <p>외형 참조 이미지 + 포즈 영상 · {pending.frames}프레임 · 16fps · {(pending.frames/16).toFixed(2)}초 · {pending.steps}스텝 · 시드 {pending.seed}</p>
      <p>{videoInfo?.summary || "입력 영상 정보 확인 중"}</p><p>{pending.prompt}</p>
      <GenerationReviewActions busy={busy} onCancel={()=>setPending(null)} onConfirm={submit}/>
    </section>}
    {embedded && <a href="/management/frame/model-management/">모델 상태 확인 및 준비</a>}
    {notice && <p role="status">{notice}</p>}
    {job ? <FunControlResult key={job} job={job} folderLink={embedded}>
      {(record,reload)=>record && <React.Fragment key={record.status}>
        <GeneratorJobControls showActions={false} service={service} id={job} state={record.status} refresh={reload}/>
        <HistoryCleanup allowSelected={false} service={service} job={job} state={record.status} onDeleted={cleaned}/>
      </React.Fragment>}
    </FunControlResult> : <HistoryCleanup allowSelected={false} service={service} onDeleted={cleaned}/>}
  </article>;
}
