import React,{useEffect,useId,useRef,useState} from "react";
import {untilAborted} from "./managementCommand.js";
import {requestErrorMessage} from "./requestError.mjs";

export default function BattlefieldReview(){
  const host=useRef(null),controller=useRef(null);
  const [state,setState]=useState(null),[error,setError]=useState(""),[revision,retry]=useState(0);
  const cameraReasonId=useId();
  useEffect(()=>{
    const abort=new AbortController();
    let timer,active=true,timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;abort.abort();},30000);
    setState(null);setError("");
    async function read(url){
      const response=await fetch(url,{signal:abort.signal,cache:"no-store"});
      if(!response.ok)throw new Error("전장 검수 번들을 불러올 수 없습니다.");
      return response.json();
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
      controller.current=module.mountReviewPage(host.current,{locale:query.get("locale") || "ko",field:query.get("field") || "all",overview:query.has("overview")});
      const refresh=()=>setState(controller.current.readState());
      refresh();timer=setInterval(refresh,1000);
    }
    untilAborted(mount(),abort.signal).catch(problem=>{if(active){clearInterval(timer);controller.current?.dispose();controller.current=null;setState(null);setError(timedOut ? "전장 검수 조회 시간이 초과됐습니다." : requestErrorMessage(problem));}}).finally(()=>clearTimeout(timeout));
    return ()=>{active=false;abort.abort();clearTimeout(timeout);clearInterval(timer);controller.current?.dispose();controller.current=null;};
  },[revision]);
  function select(field){
    controller.current.selectField(field);
    const url=new URL(location.href);url.searchParams.set("field",field);history.replaceState(null,"",url);
    setState(controller.current.readState());
  }
  const back=new URL(location.href);back.pathname="/management/frame/map-review/";back.searchParams.set("mapKind","field");back.searchParams.delete("field");
  return <article><a href={back.href}>지도 검수로 돌아가기</a><h1>전투필드 검수</h1>
    {error && <div role="alert"><p>{error} 재시도가 계속 실패하면 페이지를 다시 열어 주세요.</p><button type="button" onClick={()=>retry(value=>value+1)}>전장 검수 다시 불러오기</button></div>}
    {!state && !error && <p role="status">전장 검수 화면을 불러오는 중입니다.</p>}
    {state && <><label>전투필드 선택<select value={state.field} onChange={e=>select(e.target.value)}>
      {state.choices.map(([name,id])=><option key={id} value={id}>{name}</option>)}</select></label>
      {!state.cameraReady && <p id={cameraReasonId}>전장 시점이 준비되면 표시와 확대를 조작할 수 있습니다.</p>}
      <fieldset disabled={!state.cameraReady} aria-describedby={!state.cameraReady ? cameraReasonId : undefined}><legend>전장 표시</legend>
        <label><input type="checkbox" checked={!!state.spawnRegionsVisible} onChange={e=>{controller.current.setSpawnRegionsVisible(e.target.checked);setState(controller.current.readState());}}/>스폰지역 보기</label>
        {[["zoom-out","축소"],["zoom-in","확대"],["reset","시점 복귀"]].map(([action,label])=><button key={action} onClick={()=>controller.current.adjustCamera(action)}>{label}</button>)}
      </fieldset><p role="status">{state.status}</p></>}
    <section ref={host} aria-label="게임 전장 검수"/>
  </article>;
}
