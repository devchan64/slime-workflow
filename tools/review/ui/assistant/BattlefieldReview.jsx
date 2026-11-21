import React,{useEffect,useRef,useState} from "react";

export default function BattlefieldReview(){
  const host=useRef(null),controller=useRef(null);
  const [state,setState]=useState(null),[error,setError]=useState("");
  useEffect(()=>{
    const abort=new AbortController();
    let timer;
    async function read(url){
      const response=await fetch(url,{signal:abort.signal,cache:"no-store"});
      if(!response.ok)throw new Error("전장 검수 번들을 불러올 수 없습니다.");
      return response.json();
    }
    async function mount(){
      const catalog=await read("/manager-source.json");
      const page=catalog.pages.find(row=>new URL(row.path,location.origin).pathname.endsWith("/battlefield-preview.html"));
      if(!page)throw new Error("전투필드 검수 번들이 없습니다.");
      const url=new URL(page.path,location.origin);
      if(url.origin!==location.origin || !/^\/ui-[a-f0-9]{16}\/review\/battlefield-preview\.html$/.test(url.pathname))throw new Error("전장 검수 경로 오류");
      const base=new URL("../",url),manifest=await read(new URL("manifest.json",base));
      const entry=manifest.pages.find(row=>new URL(row.path,base).pathname===url.pathname);
      const path=manifest.componentModules?.[entry?.id];
      if(manifest.schemaVersion!==2 || manifest.kind!=="slime-ui-review" || !/^assets\/[\w-]+\.js$/.test(path) ||
        !manifest.files.some(file=>file.path===path && /^[a-f0-9]{64}$/.test(file.sha256)))throw new Error("검증된 전장 모듈을 찾을 수 없습니다.");
      const module=await import(new URL(path,base).href);
      if(abort.signal.aborted)return;
      const query=new URLSearchParams(location.search);
      controller.current=module.mountReviewPage(host.current,{locale:query.get("locale") || "ko",field:query.get("field") || "meadow-crossroads",overview:query.has("overview")});
      const refresh=()=>setState(controller.current.readState());
      refresh();timer=setInterval(refresh,1000);
    }
    mount().catch(problem=>{if(!abort.signal.aborted)setError(problem.message);});
    return ()=>{abort.abort();clearInterval(timer);controller.current?.dispose();controller.current=null;};
  },[]);
  function select(field){
    controller.current.selectField(field);
    const url=new URL(location.href);url.searchParams.set("field",field);history.replaceState(null,"",url);
    setState(controller.current.readState());
  }
  const back=new URL(location.href);back.pathname="/management/frame/map-review/";back.searchParams.set("mapKind","field");back.searchParams.delete("field");
  return <article><a href={back.href}>지도 검수로 돌아가기</a><h1>전투필드 검수</h1>
    {error && <p role="alert">{error}</p>}
    {state && <><label>전투필드 선택<select value={state.field} onChange={e=>select(e.target.value)}>
      {state.choices.map(([name,id])=><option key={id} value={id}>{name}</option>)}</select></label>
      <fieldset disabled={!state.cameraReady}><legend>전장 표시</legend>
        <label><input type="checkbox" checked={!!state.spawnRegionsVisible} onChange={e=>{controller.current.setSpawnRegionsVisible(e.target.checked);setState(controller.current.readState());}}/>스폰지역 보기</label>
        {[["zoom-out","축소"],["zoom-in","확대"],["reset","시점 복귀"]].map(([action,label])=><button key={action} onClick={()=>controller.current.adjustCamera(action)}>{label}</button>)}
      </fieldset><p role="status">{state.status}</p></>}
    <section ref={host} aria-label="게임 전장 검수"/>
  </article>;
}
