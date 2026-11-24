import React,{useEffect,useId,useRef,useState} from "react";
import {untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";
import {validBattlefieldState,battlefieldLoadFailed,sameBattlefieldState} from "./battlefieldState.mjs";
import {restoreLostFocus} from "./restoreLostFocus.mjs";

export function BattlefieldControls({state,controlsRef,selectRef,cameraReasonId,onSelect,onRetry,onSpawn,onCamera}){
  const failed=battlefieldLoadFailed(state);
  return <div ref={controlsRef} className="battlefield-controls"><label className="battlefield-select">전투필드 선택<select ref={selectRef} value={state.field} onChange={event=>onSelect(event.target.value)}>
    {state.choices.map(([name,id])=><option key={id} value={id}>{name}</option>)}</select></label>
    {!state.cameraReady && <p id={cameraReasonId}>{failed ? "전장 로드에 실패해 시점 조작을 사용할 수 없습니다. 다시 불러오거나 다른 전장을 선택하세요." : "전장 시점이 준비되면 표시와 확대를 조작할 수 있습니다."}</p>}
    {failed && <button type="button" onClick={onRetry}>현재 전장 다시 불러오기</button>}
    <fieldset disabled={!state.cameraReady} aria-describedby={!state.cameraReady ? cameraReasonId : undefined}><legend>전장 표시</legend>
      <label className="battlefield-checkbox"><input type="checkbox" checked={state.spawnRegionsVisible} onChange={event=>onSpawn(event.target.checked)}/>스폰지역 보기</label>
      <div className="ui-action-row" role="group" aria-label="전장 시점">
        {[["zoom-out","축소"],["zoom-in","확대"],["reset","시점 복귀"]].map(([action,label])=><button key={action} onClick={()=>onCamera(action)}>{label}</button>)}
      </div>
    </fieldset><p role={failed ? "alert" : "status"}>{state.status}</p></div>;
}

export function BattlefieldError({error,cleanupFailed,retryRef,onRetry,href}){
  return <div><p role="alert">{error}{!cleanupFailed && " 재시도가 계속 실패하면 페이지를 다시 열어 주세요."}</p>{cleanupFailed ? <a ref={retryRef} href={href}>전장 검수 페이지 다시 열기</a> : <button ref={retryRef} type="button" onClick={onRetry}>전장 검수 다시 불러오기</button>}</div>;
}

export default function BattlefieldReview(){
  const host=useRef(null),controller=useRef(null),pollTimer=useRef(null),controls=useRef(null),selectRef=useRef(null),retryRef=useRef(null),restoreFocus=useRef(false),retryPending=useRef(false);
  const [state,setState]=useState(null),[error,setError]=useState(""),[revision,retry]=useState(0);
  const [cleanupFailed,setCleanupFailed]=useState(false);
  const cameraReasonId=useId();
  useEffect(()=>{document.title="전투필드 검수";},[]);
  useEffect(()=>{
    if(!restoreFocus.current || (!state && !error))return;
    restoreFocus.current=false;restoreLostFocus(document,error ? retryRef.current : selectRef.current);
  },[state,error]);
  function dispose(){
    const previous=controller.current;controller.current=null;
    if(!previous)return null;
    try{previous.dispose();return null;}catch(problem){return problem;}
  }
  function fail(problem,mountIncomplete=false){
    if(controls.current?.contains(document.activeElement))restoreFocus.current=true;
    clearInterval(pollTimer.current);pollTimer.current=null;
    const cleanupError=dispose();setCleanupFailed(Boolean(cleanupError || mountIncomplete));setState(null);
    setError(requestErrorMessage(problem)+(cleanupError ? " · 전장 화면 정리에 실패했습니다. 페이지를 다시 열어 주세요. "+requestErrorMessage(cleanupError) : mountIncomplete ? " · 시작 중 화면 정리 여부를 확인할 수 없습니다. 페이지를 다시 열어 주세요." : ""));
  }
  function refresh(expectedField){
    const next=controller.current.readState();
    if(!validBattlefieldState(next))throw new Error("전장 검수 상태 형식을 확인할 수 없습니다.");
    if(expectedField!=null && next.field!==expectedField)throw new Error("선택한 전장 상태를 확인할 수 없습니다.");
    setState(previous=>sameBattlefieldState(previous,next) ? previous : next);
  }
  useEffect(()=>{
    const abort=new AbortController();
    let active=true,timedOut=false,mountIncomplete=false;
    const timeout=setTimeout(()=>{timedOut=true;abort.abort();},30000);
    setState(null);setError("");setCleanupFailed(false);
    async function read(url){
      const response=await untilAborted(fetch(url,{signal:abort.signal,cache:"no-store"}),abort.signal);
      if(!response.ok)throw new Error("전장 검수 번들을 불러올 수 없습니다.");
      return untilAborted(response.json(),abort.signal);
    }
    async function mount(){
      const catalog=await read("/manager-source.json");
      if(!Array.isArray(catalog?.pages))throw new Error("전장 검수 목록 형식을 확인할 수 없습니다.");
      const page=catalog.pages.find(row=>new URL(row.path,location.origin).pathname.endsWith("/battlefield-preview.html"));
      if(!page)throw new Error("전투필드 검수 번들이 없습니다.");
      const url=new URL(page.path,location.origin);
      if(url.origin!==location.origin || !/^\/ui-[a-f0-9]{16}\/review\/battlefield-preview\.html$/.test(url.pathname))throw new Error("전장 검수 경로 오류");
      const base=new URL("../",url),manifest=await read(new URL("manifest.json",base));
      if(!Array.isArray(manifest?.pages) || !Array.isArray(manifest?.files))throw new Error("전장 검수 manifest 형식을 확인할 수 없습니다.");
      const entry=manifest.pages.find(row=>new URL(row.path,base).pathname===url.pathname);
      const path=manifest.componentModules?.[entry?.id];
      if(manifest.schemaVersion!==2 || manifest.kind!=="slime-ui-review" || !/^assets\/[\w-]+\.js$/.test(path) ||
        !manifest.files.some(file=>file.path===path && /^[a-f0-9]{64}$/.test(file.sha256)))throw new Error("검증된 전장 모듈을 찾을 수 없습니다.");
      const module=await import(new URL(path,base).href);
      if(abort.signal.aborted)return;
      if(typeof module.mountReviewPage!=="function")throw new Error("전장 검수 화면을 시작할 수 없습니다.");
      const query=new URLSearchParams(location.search);
      mountIncomplete=true;
      controller.current=module.mountReviewPage(host.current,{locale:query.get("locale") || "ko",field:query.get("field") || "all",overview:query.has("overview")});
      if(!controller.current || ["dispose","readState","selectField","setSpawnRegionsVisible","adjustCamera"].some(name=>typeof controller.current[name]!=="function"))throw new Error("전장 검수 조작을 확인할 수 없습니다.");
      mountIncomplete=false;
      refresh();pollTimer.current=setInterval(()=>{try{refresh();}catch(problem){fail(problem);}},1000);
    }
    untilAborted(mount(),abort.signal).catch(problem=>{if(active)fail(timedOut ? new Error("전장 검수 조회 시간이 초과됐습니다.") : problem,mountIncomplete);}).finally(()=>{clearTimeout(timeout);if(active)retryPending.current=false;});
    return ()=>{active=false;abort.abort();clearTimeout(timeout);clearInterval(pollTimer.current);pollTimer.current=null;dispose();};
  },[revision]);
  function select(field){
    try{controller.current.selectField(field);refresh(field);const url=new URL(location.href);url.searchParams.set("field",field);history.replaceState(null,"",url);}
    catch(problem){fail(problem);}
  }
  const back=new URL(location.href);back.pathname="/management/frame/map-review/";back.searchParams.set("mapKind","field");back.searchParams.delete("field");
  return <article className="battlefield-review"><a href={back.href}>지도 검수로 돌아가기</a><h1>전투필드 검수</h1>
    {error && <BattlefieldError error={error} cleanupFailed={cleanupFailed} retryRef={retryRef} href={location.href} onRetry={event=>{if(retryPending.current)return;retryPending.current=true;restoreFocus.current=document.activeElement===event.currentTarget;setError("");retry(value=>value+1);}}/>}
    {!state && !error && <p role="status">전장 검수 화면을 불러오는 중입니다.</p>}
    {state && <BattlefieldControls state={state} controlsRef={controls} selectRef={selectRef} cameraReasonId={cameraReasonId} onSelect={select}
      onRetry={event=>{const restore=document.activeElement===event.currentTarget;select(state.field);if(restore)requestAnimationFrame(()=>restoreLostFocus(document,selectRef.current));}}
      onSpawn={visible=>{try{controller.current.setSpawnRegionsVisible(visible);refresh();}catch(problem){fail(problem);}}}
      onCamera={action=>{try{controller.current.adjustCamera(action);}catch(problem){fail(problem);}}}/>}
    <section key={revision} ref={host} hidden={Boolean(error)} aria-label="게임 전장 검수"/>
  </article>;
}
