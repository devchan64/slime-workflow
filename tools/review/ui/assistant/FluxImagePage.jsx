import React,{useEffect,useRef,useState} from "react";
import GpuQueueSummary from "./GpuQueueSummary.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import GeneratorJobResult from "./GeneratorJobResult.jsx";
import {managementCommand} from "./managementCommand.js";

import readReference from "./readReference.js";

function pngFile(encoded,name){
  return new File([Uint8Array.from(atob(encoded),char=>char.charCodeAt(0))],name,{type:"image/png"});
}

export default function FluxImagePage(){
  const service=location.pathname.match(/\/management\/frame\/(flux-[a-z]+)-generator/)?.[1] || "flux-image";
  const [profile,setProfile]=useState(null),[attempt,setAttempt]=useState(0);
  const seamless=service==="flux-seamless";
  const query=new URLSearchParams(location.search);
  const [form,setForm]=useState({prompt:"",translation_source_ko:"",width:768,height:768,steps:16,seed:10107,tag:""});
  const [files,setFiles]=useState([]),[review,setReview]=useState(null);
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const [job,setJob]=useState(query.get("job") || "");
  const [guideQuery,setGuideQuery]=useState(""),[guidePage,setGuidePage]=useState(0),[pageSize,setPageSize]=useState(8);
  const [selectedGuide,setSelectedGuide]=useState("");
  const [stage,setStage]=useState("");
  const [layout,setLayout]=useState(""),[subject,setSubject]=useState("");
  const sending=useRef(false);
  const fileInput=useRef(null);
  const [historyRevision,setHistoryRevision]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();
    async function load(){
      try{
        const response=await fetch("/management/assistant/flux-defaults/"+service,{signal:controller.signal});
        if(!response.ok)throw new Error("생성기 기본 입력을 불러올 수 없습니다.");
        const defaults=await response.json();
        setForm(current=>({...current,prompt:defaults.prompt,width:defaults.width,height:defaults.height}));
        setStage(defaults.stages?.[0]?.id || "");
        setLayout(defaults.layouts?.[0] || "");setSubject(defaults.subject || "");
        setProfile(defaults);setNotice("");
      }catch(error){if(!controller.signal.aborted)setNotice(error.message);}
    }
    load();return ()=>controller.abort();
  },[service,attempt]);
  async function readJob(id){
    const response=await fetch("/management/assistant/flux-image-input/"+encodeURIComponent(id)+"?service="+service,{cache:"no-store"});
    const record=await response.json();
    if(!response.ok)throw new Error(record.detail || "저장된 입력을 확인할 수 없습니다.");
    const files=record.images.map((encoded,index)=>pngFile(encoded,"reference-"+(index+1)+".png"));
    return {id:record.id,request:record.request,files};
  }
  function restore(input,record){
    setForm(seamless?{...input,width:512,height:512}:input);setFiles(seamless?[]:record.files);if(fileInput.current)fileInput.current.value="";
    setJob(record.id);setNotice(seamless?"프롬프트와 시드를 복원했습니다. 새 타일은 512×512 무참조로 생성합니다.":"선택한 이력의 입력과 참조 이미지를 불러왔습니다.");
  }
  function edit(key,value){setForm(current=>({...current,[key]:value}));}
  const terms=guideQuery.toLowerCase().trim().split(/\s+/);
  const guides=(profile?.guides || []).filter(item=>terms.every(term=>
    [item.id,item.label,item.roof,item.entrance,item.version,item.source,item.role].join(" ").toLowerCase().includes(term)));
  function guideUrl(id){return "/management/assistant/"+service+"-guide/"+encodeURIComponent(id);}
  async function applyReferenceGuide(){
    setBusy(true);setNotice("");
    try{
      const response=await fetch(guideUrl(selectedGuide));
      if(!response.ok)throw new Error("참조 가이드를 불러올 수 없습니다.");
      const file=new File([await response.blob()],selectedGuide+".png",{type:"image/png"});
      setFiles(current=>[file,...current.slice(1)]);fileInput.current.value="";
      if(profile.rolePrompt)setForm(current=>({...current,prompt:current.prompt.includes(profile.rolePrompt)?current.prompt:[current.prompt.trim(),profile.rolePrompt].filter(Boolean).join(" ")}));
    }catch(error){setNotice(error.message);}
    finally{setBusy(false);}
  }
  async function defaultFace(){
    setBusy(true);setNotice("");
    try{
      const response=await fetch("/management/assistant/flux-expression-face");
      if(!response.ok)throw new Error("기본 얼굴 이미지를 불러올 수 없습니다.");
      setFiles([new File([await response.blob()],"default-face-front-v1.png",{type:"image/png"})]);fileInput.current.value="";
    }catch(error){setNotice(error.message);}
    finally{setBusy(false);}
  }
  async function applyStage(){
    setBusy(true);setNotice("");
    try{
      const response=await fetch("/management/assistant/flux-mannequin-stage/"+encodeURIComponent(stage));
      if(!response.ok)throw new Error("마네킨 제작 단계의 참조를 불러올 수 없습니다.");
      const {prompt,width,height,images}=await response.json();
      const references=images.map((encoded,index)=>pngFile(encoded,stage+"-"+(index+1)+".png"));
      setFiles(references);setForm(current=>({...current,prompt,width,height}));fileInput.current.value="";
    }catch(error){setNotice(error.message);}
    finally{setBusy(false);}
  }
  async function applyGuide(){
    setBusy(true);setNotice("");
    try{
      const response=await fetch("/management/assistant/flux-billboard-guide",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({layout,subject})});
      if(!response.ok)throw new Error((await response.json()).detail || "가이드를 불러올 수 없습니다.");
      const {prompt,image}=await response.json();
      const guide=pngFile(image,layout+".png");
      setFiles(current=>[guide,...current.slice(1)]);edit("prompt",prompt);fileInput.current.value="";
    }catch(error){setNotice(error.message);}
    finally{setBusy(false);}
  }
  async function preview(event){
    event.preventDefault();setNotice("");setBusy(true);
    try{
      if(files.length>2)throw new Error("참조 이미지는 두 장까지 선택하세요.");
      const {translation_source_ko,...input}=form;
      const payload={...input,width:Number(input.width),height:Number(input.height),seed:Number(input.seed),steps:Number(form.steps),
        images:await Promise.all(files.map(readReference)),action:"generate"};
      if(translation_source_ko.trim())payload.translation_source_ko=translation_source_ko.trim();
      const response=await fetch("/management/assistant/flux-image-preview?service="+service,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      const result=await response.json();
      if(!response.ok)throw new Error(result.detail || "입력을 확인하세요.");
      setReview({payload,result});
    }catch(problem){setNotice(problem.message);}
    finally{setBusy(false);}
  }
  async function submit(){
    if(!review || sending.current)return;
    sending.current=true;setBusy(true);
    try{
      const result=await managementCommand(service,"generate",review.payload);
      if(!result.id)throw new Error("작업 ID를 확인할 수 없습니다.");
      setJob(result.id);setNotice("공용 GPU 대기열에 등록했습니다.");
    }catch(problem){setNotice(problem.message+" · 생성 이력에서 접수 여부를 확인하세요.");}
    finally{sending.current=false;setBusy(false);setReview(null);}
  }
  return <article><a href={"/management/assistant/"+(query.has("session")?"?"+new URLSearchParams({session:query.get("session")}):"")}>헤르메스 대화</a>
    <h1>FLUX {profile?.label} 생성</h1><GeneratorChangelog generator={service+"-generator"}/>
    {profile && <p>{profile.description}</p>}
    {!profile && notice && <button onClick={()=>setAttempt(current=>current+1)}>기본 입력 다시 불러오기</button>}
    <form onSubmit={preview}><fieldset disabled={!profile || busy || Boolean(review)}>
      {profile?.guides && <section><h2>{profile.rolePrompt?"신체 비율 기준":"건물 배치 가이드"}</h2>
        <label>가이드 검색 <input value={guideQuery} onChange={e=>{setGuideQuery(e.target.value);setGuidePage(0);setSelectedGuide("");}}/></label>
        <label>페이지당 가이드 <select value={pageSize} onChange={e=>{setPageSize(Number(e.target.value));setGuidePage(0);setSelectedGuide("");}}>{[4,8,16,32].map(size=><option key={size}>{size}</option>)}</select></label>
        <p>검색 결과 {guides.length}건</p>
        {guides.slice(guidePage*pageSize,(guidePage+1)*pageSize).map(item=><button type="button" key={item.id} aria-pressed={selectedGuide===item.id} onClick={()=>setSelectedGuide(item.id)}>
          <img width="110" loading="lazy" src={guideUrl(item.id)+"?thumbnail=true"} alt=""/>{item.label} · {item.id}</button>)}
        <button type="button" disabled={!guidePage} onClick={()=>{setGuidePage(guidePage-1);setSelectedGuide("");}}>이전</button>
        <button type="button" disabled={(guidePage+1)*pageSize>=guides.length} onClick={()=>{setGuidePage(guidePage+1);setSelectedGuide("");}}>다음</button>
        {profile.rolePrompt && selectedGuide && <figure><img width="240" src={guideUrl(selectedGuide)} alt="선택한 신체 비율 기준"/><figcaption>{guides.filter(item=>item.id===selectedGuide).map(item=>[item.role,item.version,item.sha256].join(" · "))}</figcaption></figure>}
        <button type="button" disabled={!selectedGuide} onClick={applyReferenceGuide}>선택한 가이드를 첫 참조에 적용</button>
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
        <p>{profile.expressions.find(item=>item.id===form.prompt)?.text}</p>
        <button type="button" onClick={defaultFace}>기본 캐릭터 정면 얼굴 불러오기</button>
      </> : <label>{service==="flux-building"?"건물 디자인 (한국어)":"프롬프트"} <textarea value={form.prompt} onChange={e=>edit("prompt",e.target.value)}/></label>}
      {service!=="flux-building" && <label>번역할 한국어 설명 <textarea value={form.translation_source_ko} onChange={e=>edit("translation_source_ko",e.target.value)}/></label>}
      {!seamless && <label>{profile?.expressions?"얼굴 참조 PNG (1장)":"참조 PNG (최대 2장)"} <input ref={fileInput} type="file" multiple={!profile?.expressions} accept="image/png" onChange={e=>setFiles(Array.from(e.target.files))}/></label>}
      {files.map((file,index)=><p key={index}>참조 {index+1} · {file.name}</p>)}
      {[["width","너비"],["height","높이"]].map(([key,label])=><label key={key}>{label} <input type="number" readOnly={seamless} required min="256" max={service==="flux-character"?2048:1664} step="16" value={form[key]} onChange={e=>edit(key,e.target.value)}/></label>)}
      {service==="flux-character" && <label>생성 스텝 <input type="number" required min="1" max="50" value={form.steps} onChange={e=>edit("steps",e.target.value)}/></label>}
      <label>시드 <input type="number" required min="0" max="4294967295" value={form.seed} onChange={e=>edit("seed",e.target.value)}/></label>
      <button type="button" onClick={()=>edit("seed",crypto.getRandomValues(new Uint32Array(1))[0])}>랜덤 시드</button>
      <label>이력 태그 <input value={form.tag} onChange={e=>edit("tag",e.target.value)}/></label>
      <button disabled={files.length < profile?.minimum || (!form.prompt.trim() && !form.translation_source_ko.trim())}>생성 요청 검토</button>
    </fieldset></form>
    {review && <section><h2>{profile?.expressions?"표정 프롬프트":"공용 화풍 적용 프롬프트"}</h2><pre>{review.result.prompt}</pre>
      {review.result.translation && <p>생성 시 번역할 내용 · {review.result.translation}</p>}
      <GpuQueueSummary/><button disabled={busy} onClick={()=>setReview(null)}>입력 수정</button>
      <button disabled={busy} onClick={submit}>확인 후 대기열에 추가</button></section>}
    {notice && <p role="status">{notice}</p>}
    {profile && !busy && !review && <GeneratorHistory key={historyRevision} service={service} readJob={readJob} restore={restore} inspectResult={record=>setJob(record.id)}/>}
    <GeneratorJobResult job={job} kind="flux" service={service} onDeleted={message=>{setJob("");setNotice(message);setHistoryRevision(value=>value+1);}}/>
  </article>;
}
