import usePageTitle from "./usePageTitle.js";
import GenerationReviewActions from "./GenerationReviewActions.jsx";
import GpuHandoffStatus from "./GpuHandoffStatus.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import ActionButton from "./ActionButton.jsx";
import ReferenceImageInput from "./ReferenceImageInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import SeedInput from "./SeedInput.jsx";
import React,{useEffect,useId,useRef,useState} from "react";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import ModelReadiness from "./ModelReadiness.jsx";
import GeneratorJobResult from "./GeneratorJobResult.jsx";
import {managementCommand} from "./managementCommand.js";
import {fluxProposalRequestId,classifyFluxProposalReceipt,verifyFluxProposal} from "./fluxProposalReceipt.mjs";
import {fluxModelReady} from "./fluxModelReady.mjs";
import {validateGpuHandoffStatus} from "./validateGpuHandoffStatus.mjs";
import {filterFluxGuides,addFluxRolePrompt} from "./fluxGuides.mjs";

import readReference from "./readReference.js";

function pngFile(encoded,name){
  return new File([Uint8Array.from(atob(encoded),char=>char.charCodeAt(0))],name,{type:"image/png"});
}

export default function FluxImagePage({serviceOverride,embedded=false,initialInputs=null,receiptScope=null,session:embeddedSession=""}={}){
  const referenceOrderHelpId=useId();
  const service=serviceOverride || location.pathname.match(/\/management\/frame\/(flux-[a-z]+)-generator/)?.[1] || "flux-image";
  const [profile,setProfile]=useState(null),[attempt,setAttempt]=useState(0);
  const [profileError,setProfileError]=useState("");
  const profileRetryRef=useRef(null),profileRetryFocus=useRef(false);
  usePageTitle(profile?.label ? "FLUX 이미지 생성 · "+profile.label : "FLUX 이미지 생성",embedded);
  const seamless=service==="flux-seamless";
  const query=new URLSearchParams(location.search);
  const session=receiptScope?.session || embeddedSession || query.get("session") || "";
  const [form,setForm]=useState({prompt:"",translation_source_ko:"",width:768,height:768,steps:16,seed:10107,tag:""});
  const [files,setFiles]=useState([]),[review,setReview]=useState(null);
  const inputRef=useRef({form,files});inputRef.current={form,files};
  const imageSelectionRevision=useRef(0);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState(""),[model,setModel]=useState(null);
  const reviewEpoch=useRef(0),interactionRef=useRef({busy,review});interactionRef.current={busy,review};
  const [job,setJob]=useState(embedded ? "" : query.get("job") || "");
  const [guideQuery,setGuideQuery]=useState(""),[guidePage,setGuidePage]=useState(0),[pageSize,setPageSize]=useState(8);
  const guideSearchRef=useRef(null),inputFormRef=useRef(null);
  useEffect(()=>{
    if(!profileRetryFocus.current || (!profile && !profileError))return;
    profileRetryFocus.current=false;
    requestAnimationFrame(()=>{if(document.activeElement===document.body)(profile ? inputFormRef.current : profileRetryRef.current)?.focus();});
  },[profile,profileError]);
  const [selectedGuide,setSelectedGuide]=useState(""),[guideNotice,setGuideNotice]=useState("");
  useEffect(()=>{setGuideNotice("");},[selectedGuide]);
  const [stage,setStage]=useState("");
  const [layout,setLayout]=useState(""),[subject,setSubject]=useState("");
  const sending=useRef(false);
  const [historyRevision,setHistoryRevision]=useState(0);
  const receiptKey=receiptScope ? `flux-proposal-receipt:${receiptScope.session}:${receiptScope.job}:${service}` : "";
  const handoffKey=session ? `flux-gpu-handoff:${session}:${receiptScope?.job || "direct"}:${service}` : "";
  const [handoffReview,setHandoffReview]=useState(null),[handoffId,setHandoffId]=useState(()=>handoffKey ? sessionStorage.getItem(handoffKey) || "" : ""),[handoffStatus,setHandoffStatus]=useState(null);
  const [receipt,setReceipt]=useState("");
  const [receiptJob,setReceiptJob]=useState("");
  const [receiptNotice,setReceiptNotice]=useState("");
  const [receiptState,setReceiptState]=useState(()=>receiptKey ? "checking" : "editing");
  async function checkReceipt(id){
    const value=await managementCommand("hermes-agent","hermes-service-receipt",{service,request_id:id});
    const checked=classifyFluxProposalReceipt(value,id,service);
    if(checked.state==="accepted"){
      setReceiptJob(checked.job);setJob(checked.job);setReceiptState("accepted");setReceiptNotice("접수된 작업을 확인했습니다.");
    }else if(checked.state==="editing"){setReceiptJob("");setReceiptState("editing");setReceiptNotice("");}
    else if(checked.state==="rejected"){setReceiptJob("");setReceiptState("rejected");setReceiptNotice("생성 요청이 검증에 실패해 접수되지 않았습니다. GPU 양도 상태와 입력을 확인하세요.");}
    else{setReceiptJob("");setReceiptState("unknown");setReceiptNotice("접수 여부를 확인할 수 없습니다. 자동 재접수하지 않습니다. 생성 이력과 접수 기록을 확인하세요.");}
    return checked;
  }
  async function refreshReceipt(){
    setReceiptState("checking");
    try{
      const id=await fluxProposalRequestId(receiptScope.session,receiptScope.job,service);
      setReceipt(id);
      const handoff=validateGpuHandoffStatus(await managementCommand("hermes-agent","hermes-gpu-handoff-status",{session_id:session,request_id:id}),session,id,service);
      if(handoff.state!=="not_found"){
        setHandoffId(id);setHandoffStatus(handoff);
      }
      const checked=await checkReceipt(id);
      if(handoff.state!=="not_found" && checked.state==="editing"){
        setReceiptState("unknown");setReceiptNotice("GPU 양도 요청의 상태를 확인하세요. 같은 제안을 다시 접수하지 않습니다.");
      }
    }catch(error){setReceiptState("unknown");setReceiptNotice(error.message || "접수 기록을 확인할 수 없습니다. 생성 이력을 확인하세요.");}
  }
  useEffect(()=>{if(receiptKey)refreshReceipt();},[]);
  async function refreshHandoff(id){
    const value=await managementCommand("hermes-agent","hermes-gpu-handoff-status",{session_id:session,request_id:id});
    setHandoffStatus(validateGpuHandoffStatus(value,session,id,service));
    if(value.job_id)setJob(value.job_id);
  }
  useEffect(()=>{if(handoffId)refreshHandoff(handoffId).catch(()=>setNotice("GPU 양도 상태를 확인할 수 없습니다. 다시 확인하세요."));},[]);
  useEffect(()=>{
    const controller=new AbortController();
    let active=true,timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    async function load(){
      setProfileError("");
      try{
        const response=await fetch("/management/assistant/flux-defaults/"+service,{signal:controller.signal});
        if(!response.ok)throw new Error("생성기 기본 입력을 불러올 수 없습니다.");
        const defaults=await response.json();
        if(!defaults || typeof defaults.label!=="string" || typeof defaults.prompt!=="string" ||
          ![defaults.width,defaults.height,defaults.minimum].every(Number.isInteger) ||
          ["guides","stages","expressions"].some(key=>defaults[key]!=null && (!Array.isArray(defaults[key]) || defaults[key].some(item=>!item || typeof item.id!=="string" || typeof item.label!=="string" || (key==="expressions" && typeof item.text!=="string")))) ||
          (defaults.layouts!=null && (!Array.isArray(defaults.layouts) || defaults.layouts.some(item=>typeof item!=="string"))))throw new Error("생성기 기본 입력 형식을 확인할 수 없습니다.");
        if(controller.signal.aborted)return;
        setForm(current=>({...current,prompt:defaults.prompt,width:defaults.width,height:defaults.height,...(initialInputs || {})}));
        setStage(defaults.stages?.[0]?.id || "");
        setLayout(defaults.layouts?.[0] || "");setSubject(defaults.subject || "");
        setProfile(defaults);
      }catch(error){if(active && (timedOut || !controller.signal.aborted))setProfileError(timedOut ? "생성기 기본 입력 조회 시간이 초과됐습니다." : error.message);}
      finally{clearTimeout(timeout);}
    }
    load();return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[service,attempt]);
  async function readJob(id){
    const inputAtStart=inputRef.current,imageAtStart=imageSelectionRevision.current,reviewAtStart=reviewEpoch.current;
    const controller=new AbortController();let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try{
    const response=await fetch("/management/assistant/flux-image-input/"+encodeURIComponent(id)+"?service="+service,{cache:"no-store",signal:controller.signal});
    const record=await response.json();
    if(!response.ok)throw new Error(record.detail || "저장된 입력을 확인할 수 없습니다.");
    const files=record.images.map((encoded,index)=>pngFile(encoded,"reference-"+(index+1)+".png"));
    return {id:record.id,request:record.request,files,inputAtStart,imageAtStart,reviewAtStart};
    }catch(error){if(timedOut)throw new Error("저장 입력 조회 시간이 초과됐습니다. 다시 조회하세요.");throw error;}
    finally{clearTimeout(timeout);}
  }
  function restore(input,record){
    if(record.reviewAtStart!==reviewEpoch.current || interactionRef.current.busy || interactionRef.current.review)throw new Error("조회 중 생성 폼에서 다른 작업이 진행되어 이력 입력을 적용하지 않았습니다.");
    if(record.inputAtStart.form!==inputRef.current.form || record.inputAtStart.files!==inputRef.current.files || record.imageAtStart!==imageSelectionRevision.current)throw new Error("입력 조회 중 작성 내용이나 참조 이미지가 변경되어 적용하지 않았습니다.");
    setForm(seamless?{...input,width:512,height:512}:input);setFiles(seamless?[]:record.files);
    setNotice(seamless?"프롬프트와 시드를 복원했습니다. 새 타일은 512×512 무참조로 생성합니다.":"선택한 이력의 입력과 참조 이미지를 불러왔습니다.");
    requestAnimationFrame(()=>inputFormRef.current?.focus());
  }
  function edit(key,value){setForm(current=>({...current,[key]:value}));}
  const guides=filterFluxGuides(profile?.guides || [],guideQuery);
  function guideUrl(id){return "/management/assistant/"+service+"-guide/"+encodeURIComponent(id);}
  async function applyReferenceGuide(){
    imageSelectionRevision.current++;
    setBusy(true);setNotice("");setGuideNotice("");
    try{
      const response=await fetch(guideUrl(selectedGuide));
      if(!response.ok)throw new Error("참조 가이드를 불러올 수 없습니다.");
      const file=new File([await response.blob()],selectedGuide+".png",{type:"image/png"});
      setFiles(current=>[file,...current.slice(1)]);
      if(profile.rolePrompt)setForm(current=>({...current,prompt:addFluxRolePrompt(current.prompt,profile.rolePrompt)}));
      setGuideNotice("선택한 가이드를 참조 이미지 1에 적용했습니다.");
    }catch(error){setGuideNotice("참조 가이드를 적용하지 못했습니다. · "+error.message);}
    finally{setBusy(false);}
  }
  async function defaultFace(){
    imageSelectionRevision.current++;
    setBusy(true);setNotice("");
    try{
      const response=await fetch("/management/assistant/flux-expression-face");
      if(!response.ok)throw new Error("기본 얼굴 이미지를 불러올 수 없습니다.");
      setFiles([new File([await response.blob()],"default-face-front-v1.png",{type:"image/png"})]);
    }catch(error){setNotice(error.message);}
    finally{setBusy(false);}
  }
  async function applyStage(){
    imageSelectionRevision.current++;
    setBusy(true);setNotice("");
    try{
      const response=await fetch("/management/assistant/flux-mannequin-stage/"+encodeURIComponent(stage));
      if(!response.ok)throw new Error("마네킨 제작 단계의 참조를 불러올 수 없습니다.");
      const {prompt,width,height,images}=await response.json();
      const references=images.map((encoded,index)=>pngFile(encoded,stage+"-"+(index+1)+".png"));
      setFiles(references);setForm(current=>({...current,prompt,width,height}));
    }catch(error){setNotice(error.message);}
    finally{setBusy(false);}
  }
  async function applyGuide(){
    imageSelectionRevision.current++;
    setBusy(true);setNotice("");
    try{
      const response=await fetch("/management/assistant/flux-billboard-guide",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({layout,subject})});
      if(!response.ok)throw new Error((await response.json()).detail || "가이드를 불러올 수 없습니다.");
      const {prompt,image}=await response.json();
      const guide=pngFile(image,layout+".png");
      setFiles(current=>[guide,...current.slice(1)]);edit("prompt",prompt);
    }catch(error){setNotice(error.message);}
    finally{setBusy(false);}
  }
  async function preview(event){
    reviewEpoch.current++;
    event.preventDefault();setNotice("");setBusy(true);
    try{
      if(receiptScope)await verifyFluxProposal(managementCommand,receiptScope,receiptScope.proposal);
      if(files.length>2)throw new Error("참조 이미지는 두 장까지 선택하세요.");
      const {translation_source_ko,...input}=form;
      const payload={...input,width:Number(input.width),height:Number(input.height),seed:Number(input.seed),steps:Number(form.steps),
        images:await Promise.all(files.map(readReference)),action:"generate"};
      if(translation_source_ko.trim())payload.translation_source_ko=translation_source_ko.trim();
      const response=await fetch("/management/assistant/flux-image-preview?service="+service,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      const result=await response.json();
      if(!response.ok)throw new Error(result.detail || "입력을 확인하세요.");
      setHandoffReview(null);
      if(session){
        const owner=await managementCommand("hermes-agent","hermes-resident-status",{session_id:session});
        if(owner.session_id!==session || !owner.resident)throw new Error("대화 모델 상태를 확인할 수 없습니다.");
        if(owner.resident_id){
          if(owner.resident.state!=="ready")throw new Error("Qwen 3.8 상주 모델 상태를 확인한 뒤 다시 검토하세요.");
          const handoff=await managementCommand("hermes-agent","hermes-gpu-handoff-preview",{session_id:session,resident_id:owner.resident_id,service,request:payload});
          if(handoff.session_id!==session || handoff.resident_id!==owner.resident_id || handoff.service!==service || !/^[a-f0-9]{64}$/.test(handoff.review_hash || ""))throw new Error("GPU 양도 검토 결과가 일치하지 않습니다.");
          setHandoffReview(handoff);
        }else if(owner.resident.state!=="not_found")throw new Error("대화 모델 상태를 확인할 수 없습니다.");
      }
      setReview({payload,result});
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  async function submit(){
    if(!review || sending.current || !fluxModelReady(model))return;
    sending.current=true;setBusy(true);
    let dispatched=false;
    try{
      if(receiptScope)await verifyFluxProposal(managementCommand,receiptScope,receiptScope.proposal);
      if(handoffReview){
        const id=receiptScope ? await fluxProposalRequestId(receiptScope.session,receiptScope.job,service) : crypto.randomUUID().replaceAll("-","");
        sessionStorage.setItem(handoffKey,id);setHandoffId(id);setHandoffStatus({state:"checking"});
        dispatched=true;
        const result=await managementCommand("hermes-agent","hermes-gpu-handoff-approve",{request_id:id,session_id:session,resident_id:handoffReview.resident_id,service,request:review.payload,review_hash:handoffReview.review_hash,confirmed:true});
        validateGpuHandoffStatus(result,session,id,service);
        if(!["approved","waiting_release","submitting","running","reload_queued","reloading","ready"].includes(result.state))throw new Error("GPU 양도 접수 여부를 확인할 수 없습니다.");
        setHandoffStatus(result);setNotice("확인한 GPU 양도 요청을 접수했습니다. 진행 상태를 확인하세요.");
      }else if(receiptKey){
        if(receiptState!=="editing")throw new Error("이전 접수 상태를 먼저 확인하세요.");
        const requestId=await fluxProposalRequestId(receiptScope.session,receiptScope.job,service);
        setReceipt(requestId);setReceiptState("checking");
        dispatched=true;
        const result=await managementCommand("hermes-agent","hermes-delegate-flux-profile",{request_id:requestId,service,request:review.payload});
        if(result.state!=="accepted" || result.service!==service || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(result.job_id || ""))throw new Error("접수 결과를 확인할 수 없습니다.");
        setReceiptJob(result.job_id);setJob(result.job_id);setReceiptState("accepted");setReceiptNotice("공용 GPU 대기열에 등록했습니다.");
      }else{
        dispatched=true;
        const result=await managementCommand(service,"generate",review.payload);
        if(!result.id)throw new Error("작업 ID를 확인할 수 없습니다.");
        setJob(result.id);setNotice("공용 GPU 대기열에 등록했습니다.");
      }
    }catch(problem){if(!dispatched)setNotice(problem.message+" · 요청은 접수되지 않았습니다.");else if(handoffReview)setNotice(problem.message+" · GPU 양도 상태를 확인하세요.");else if(receiptKey){setReceiptState("unknown");setReceiptNotice(problem.message+" · 생성 이력에서 접수 여부를 확인하세요.");}else setNotice(problem.message+" · 생성 이력에서 접수 여부를 확인하세요.");}
    finally{sending.current=false;setBusy(false);setReview(null);setHandoffReview(null);}
  }
  return <article className={"flux-page"+(embedded ? "" : " flux-standalone")}><a href={"/management/assistant/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화</a>
    <h1 className={embedded ? "embedded-page-title" : undefined}>FLUX 이미지 생성 · {profile?.label}</h1><GeneratorChangelog generator={service+"-generator"}/>{embedded ? <details><summary>모델 상태 · {model ? (fluxModelReady(model) ? "준비 완료" : "준비 필요") : "확인 필요"}</summary><ModelReadiness service={service} onStatus={setModel}/></details> : <ModelReadiness service={service} onStatus={setModel}/>}
    {profile && <p>{profile.description}</p>}
    {!profile && (profileError ? <div role="alert">{profileError} <button ref={profileRetryRef} type="button" onClick={()=>{profileRetryFocus.current=true;setAttempt(current=>current+1);}}>기본 입력 다시 불러오기</button></div> : <p role="status">기본 입력을 불러오는 중입니다.</p>)}
    {handoffId && <GpuHandoffStatus session={session} id={handoffId} service={service} status={handoffStatus} onUpdate={value=>{setHandoffStatus(value);if(value.job_id)setJob(value.job_id);}}
      onClose={receiptKey && handoffStatus?.state!=="withdrawn" ? undefined : ()=>{sessionStorage.removeItem(handoffKey);setHandoffId("");setHandoffStatus(null);if(receiptKey){setReceiptState("unknown");setReceiptNotice("이 제안의 양도 요청은 철회됐습니다. 새 작업은 생성기 화면에서 요청하세요.");}}}/>}
    {receiptKey && receiptState!=="editing" && <section aria-label="FLUX 제안 접수 상태"><p>접수 ID · {receiptState==="accepted"?"접수 확인됨":receiptState==="rejected"?"접수 거절됨":receiptState==="checking"?"확인 중":"확인 필요"}</p>{receipt ? <JobIdentifier id={receipt} label="접수 ID" compact/> : <p>확인 불가</p>}{receiptState==="accepted" && receiptJob && <div><p>접수 작업</p><JobIdentifier id={receiptJob} compact/> <button type="button" onClick={()=>setJob(receiptJob)}>이 작업 결과 조회</button></div>}{receiptNotice && <p role="status">{receiptNotice}</p>}<p>같은 제안은 중복 접수를 막기 위해 다시 제출할 수 없습니다. 다른 작업은 생성기 화면에서 새로 요청하세요.</p><button type="button" disabled={busy || receiptState==="checking"} onClick={refreshReceipt}>접수 상태 다시 확인</button></section>}
    <form ref={inputFormRef} tabIndex={-1} aria-label="생성 입력" onSubmit={preview}><fieldset disabled={!profile || busy || Boolean(review) || Boolean(handoffId) || (receiptKey && receiptState!=="editing")}>
      {profile?.guides && <section className="flux-guides"><h2>{profile.rolePrompt?"신체 비율 기준":"건물 배치 가이드"}</h2>
        <div className="flux-guides-toolbar">
        <label>가이드 검색 <input ref={guideSearchRef} value={guideQuery} onChange={e=>{setGuideQuery(e.target.value);setGuidePage(0);setSelectedGuide("");}}/></label>
        <label>페이지당 가이드 <select value={pageSize} onChange={e=>{setPageSize(Number(e.target.value));setGuidePage(0);setSelectedGuide("");}}>{[4,8,16,32].map(size=><option key={size}>{size}</option>)}</select></label>
        {guideQuery && <button type="button" onClick={()=>{setGuideQuery("");setGuidePage(0);setSelectedGuide("");guideSearchRef.current?.focus();}}>검색 초기화</button>}
        </div>
        <p>검색 결과 {guides.length}건</p>
        {!guides.length && <p role="status">일치하는 가이드가 없습니다. 검색어를 바꿔 보세요.</p>}
        <div className="flux-guides-list">
        {guides.slice(guidePage*pageSize,(guidePage+1)*pageSize).map(item=><button type="button" key={item.id} aria-pressed={selectedGuide===item.id} onClick={()=>setSelectedGuide(item.id)}>
          <img width="110" loading="lazy" src={guideUrl(item.id)+"?thumbnail=true"} alt=""/><span>{item.label} · {item.id}</span></button>)}
        </div><nav className="flux-guides-pages" aria-label="가이드 페이지 이동">
        <button type="button" disabled={!guidePage} onClick={()=>{setGuidePage(guidePage-1);setSelectedGuide("");}}>이전</button>
        <span aria-live="polite">{guides.length ? guidePage+1 : 0} / {Math.ceil(guides.length/pageSize)} 페이지</span>
        <button type="button" disabled={(guidePage+1)*pageSize>=guides.length} onClick={()=>{setGuidePage(guidePage+1);setSelectedGuide("");}}>다음</button>
        </nav>
        {profile.rolePrompt && selectedGuide && <figure><img width="240" src={guideUrl(selectedGuide)} alt="선택한 신체 비율 기준"/><figcaption>{guides.filter(item=>item.id===selectedGuide).map(item=>[item.role,item.version,item.sha256].join(" · "))}</figcaption></figure>}
        <button type="button" disabled={!selectedGuide} onClick={applyReferenceGuide}>선택한 가이드를 첫 참조에 적용</button>
        {guideNotice && <p role="status">{guideNotice}</p>}
      </section>}
      {profile?.stages && <>
        <label>마네킨 제작 단계 <select value={stage} onChange={e=>setStage(e.target.value)}>{profile.stages.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        <button type="button" onClick={applyStage}>선택한 단계와 프롬프트 예시 불러오기</button>
      </>}
      {profile?.layouts && <>
        <label>점유 가이드 <select value={layout} onChange={e=>setLayout(e.target.value)}>{profile.layouts.map(value=><option key={value}>{value}</option>)}</select></label>
        <label>생성 대상 <input value={subject} onChange={e=>setSubject(e.target.value)}/></label>
        <button type="button" disabled={!subject.trim()} onClick={applyGuide}>선택한 가이드와 프롬프트 적용</button>
      </>}
      {profile?.expressions ? <>
        <label>표정 <select value={form.prompt} onChange={e=>edit("prompt",e.target.value)}>{profile.expressions.map(item=><option value={item.id} key={item.id}>{item.label}</option>)}</select></label>
        <p>{profile.expressions.find(item=>item.id===form.prompt)?.text}<PromptWordCount text={profile.expressions.find(item=>item.id===form.prompt)?.text} label="기본 프롬프트"/></p>
        <button type="button" onClick={defaultFace}>기본 캐릭터 정면 얼굴 불러오기</button>
      </> : <label>{service==="flux-building"?"건물 디자인 (한국어)":"프롬프트"} <textarea value={form.prompt} onChange={e=>edit("prompt",e.target.value)}/><PromptWordCount text={form.prompt}/></label>}
      {service!=="flux-building" && <label>번역할 한국어 설명 <textarea value={form.translation_source_ko} onChange={e=>edit("translation_source_ko",e.target.value)}/><PromptWordCount text={form.translation_source_ko}/><small>입력하면 번역을 먼저 진행하고 번역문을 위 프롬프트 뒤에 추가합니다.</small></label>}
      {profile?.rolePrompt && form.prompt.trim()===profile.rolePrompt.trim() && !form.translation_source_ko.trim() && <p role="status">현재 입력에는 신체 비율 참조 안내만 있습니다. 원하는 캐릭터 외형이나 자세를 추가할 수 있습니다.</p>}
      {!seamless && <section aria-label="참조 이미지"><p>{profile?.expressions?"얼굴 참조 PNG (1장)":"참조 PNG (최대 2장)"}</p><div className="reference-image-slots">
        {Array.from({length:profile?.expressions?1:2},(_,index)=><ReferenceImageInput key={index} label={profile?.expressions?"얼굴 참조 이미지":"참조 이미지 "+(index+1)}
          accept="image/png" maxBytes={3000000} source={files[index]} disabled={!profile || busy || Boolean(review) || (index>0 && !files[0])} describedBy={index===1 && !files[0] ? referenceOrderHelpId : undefined} onSelectionStart={()=>{imageSelectionRevision.current++;}}
          onChange={file=>{setGuideNotice("");setFiles(current=>{const next=[...current];if(file)next[index]=file;else next.splice(index,1);return next;});}}/>)}
      </div>{!profile?.expressions && !files[0] && <p id={referenceOrderHelpId}>두 번째 참조를 추가하려면 먼저 첫 번째 참조를 선택하세요.</p>}</section>}
      {[["width","너비"],["height","높이"]].map(([key,label])=><label key={key}>{label} <input type="number" readOnly={seamless} required min="256" max={service==="flux-character"?2048:1664} step="16" value={form[key]} onChange={e=>edit(key,e.target.value)}/></label>)}
      {service==="flux-character" ? <label>생성 스텝 <input type="number" required min="1" max="50" value={form.steps} onChange={e=>edit("steps",e.target.value)}/></label> : <p>생성 스텝: 16</p>}
      <p>FLUX.3 Image Klein Distilled의 <a href="https://huggingface.co/black-forest-labs/flux-3-image-klein" target="_blank" rel="noreferrer">모델 카드</a> 권장값은 16스텝입니다.</p>
      <p>모델 카드는 구체적인 장면 설명을 권장합니다. 필요한 피사체, 구도, 배경과 조명을 프롬프트에 적어 주세요. 자동 프롬프트 확장은 사용하지 않습니다.</p>
      <SeedInput value={form.seed} max={4294967295} onChange={value=>edit("seed",value)}/>
      <label>이력 태그 <input value={form.tag} onChange={e=>edit("tag",e.target.value)}/></label>
      <ActionButton type="submit" reasons={[
        !profile && "생성기 설정을 확인 중입니다. 잠시 기다리거나 다시 불러오세요.",
        profile && files.length < profile.minimum && "필수 참조 이미지를 선택하세요.",
        !form.prompt.trim() && !form.translation_source_ko.trim() && "프롬프트 또는 번역할 설명을 입력하세요."
      ]}>생성 요청 검토</ActionButton>
    </fieldset></form>
    {review && <section><h2>{profile?.expressions?"표정 프롬프트":"공용 화풍 적용 프롬프트"}</h2><pre>{review.result.prompt}</pre><p><PromptWordCount text={review.result.prompt} label={review.result.translation ? "번역 전 프롬프트" : "최종 프롬프트"}/>{review.result.translation && " · 번역 후 최종 단어 수는 생성 시 확정됩니다."}</p>
      {review.result.translation && <p>생성 시 번역할 내용 · {review.result.translation}</p>}
      <GpuQueueSummary/>{handoffReview && <p>동의하면 진행 중인 헤르메스 대화가 끝난 뒤 Qwen 3.8을 해제하고 {profile?.label || "FLUX"} 생성을 실행합니다. 작업이 끝나면 Qwen 3.8을 다시 GPU에 적재합니다.</p>}<GenerationReviewActions busy={busy} onCancel={()=>{setReview(null);setHandoffReview(null);}} onConfirm={submit} confirmLabel={handoffReview ? "해제·생성·재적재에 동의" : "확인 후 대기열에 추가"} disabledReason={!fluxModelReady(model) ? "모델 준비 상태를 확인하고 필요한 준비를 완료하세요." : handoffId ? "이전 GPU 양도 상태를 먼저 확인하세요." : ""}/></section>}
    {notice && <p role="status">{notice}</p>}
    {profile && <fieldset className="flux-history-controls" disabled={busy || Boolean(review)}><GeneratorHistory allowPriority onSelectedDeleted={(id,message)=>{if(job===id)setJob("");setNotice(message);setHistoryRevision(value=>value+1);}} key={historyRevision} service={service} readJob={readJob} resultId={job} openResult={setJob} onCloseResult={()=>setJob("")} restore={restore} renderResult={(id,close)=><section aria-label="선택한 FLUX 작업 결과"><button type="button" onClick={close}>결과 닫기</button><GeneratorJobResult selectionControls job={id} kind="flux" service={service} readJob={readJob} onDeleted={message=>{setJob("");setNotice(message);setHistoryRevision(value=>value+1);}}/></section>}/></fieldset>}
    <GeneratorJobResult selectionControls job="" kind="flux" service={service} onDeleted={message=>{setJob("");setNotice(message);setHistoryRevision(value=>value+1);}}/>
  </article>;
}
