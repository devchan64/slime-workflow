import React from "react";

/** 현재 페이지의 작업 흐름으로 이동한다. 이동은 생성이나 작업 선택을 실행하지 않는다. */
export default function GeneratorSectionNavigation({inputRef,historyRef,resultRef,inputReady=true,resultReady=false,openOnNavigate=false}){
  const targets=[
    {label:'생성 입력',ref:inputRef,ready:inputReady,reason:'생성 입력을 불러오는 중입니다.'},
    {label:'생성 이력',ref:historyRef,ready:true},
    {label:'작업 결과',ref:resultRef,ready:resultReady,reason:'이력에서 작업 결과를 먼저 선택하세요.'},
  ];
  function move(target){
    // 결과가 이력 조회 중이면 조회 상태가 표시되는 이력으로 이동한다.
    const waitingForResult=target.label==='작업 결과' && !target.ref.current;
    const region=waitingForResult ? historyRef.current : target.ref.current;
    if(!region)return;
    if(openOnNavigate || waitingForResult){
      for(let node=region;node;node=node.parentElement)if(node.tagName==='DETAILS')node.open=true;
      if(target.label==='생성 이력' || waitingForResult){const detail=region.querySelector('details');if(detail)detail.open=true;}
    }
    const focus=target.label==='생성 이력' || waitingForResult ? region.querySelector('summary') || region : region;
    focus.scrollIntoView({block:'start'});
    focus.focus({preventScroll:true});
  }
  return <nav className="generator-section-navigation" aria-label="생성기 영역 이동">
    <span>바로 이동</span>
    {targets.map(target=><button key={target.label} type="button" disabled={!target.ready} title={!target.ready ? target.reason : undefined} onClick={()=>move(target)}>{target.label}</button>)}
    {!resultReady && <small>결과는 이력에서 작업을 선택하면 볼 수 있습니다.</small>}
  </nav>;
}
