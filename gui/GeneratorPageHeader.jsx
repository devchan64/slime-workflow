import usePageTitle from "./usePageTitle.js";
import React from "react";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import ModelReadiness from "./ModelReadiness.jsx";

export default function GeneratorPageHeader({title,description,service,generator,embedded,model,onStatus,session:embeddedSession}) {
  usePageTitle(title,embedded);
  const session=embeddedSession ?? new URLSearchParams(location.search).get("session");
  const conversation="/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"");
  const readiness=model ? (model.generation_ready ?? model.ready) ? "준비 완료" : "준비 필요" : "확인 필요";
  return <header className="generator-page-header">
    {!embedded && <nav aria-label="워크플로우 탐색"><a href={conversation}>헤르메스 대화로 돌아가기</a></nav>}
    <div><h1>{title}</h1><p>{description}</p></div>
    <div className="generator-page-tools">
      <details><summary>모델 상태 · {readiness}</summary><ModelReadiness session={session} hasStatusSummary service={service} onStatus={onStatus}/></details>
      <GeneratorChangelog generator={generator}/>
    </div>
  </header>;
}
