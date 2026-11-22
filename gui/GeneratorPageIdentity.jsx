import React from "react";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import {generatorPageIdentity} from "./generatorPageRegistry.mjs";

/** 생성기 페이지 공통 식별 영역. 모델·작업 기능은 각 공용 컴포넌트에서 관리한다. */
export default function GeneratorPageIdentity({service,embedded=false,session="",showReturn=!embedded,description,withNavigation=false,returnHref,returnLabel="헤르메스 대화로 돌아가기"}){
  const {title,changelog}=generatorPageIdentity(service);
  const destination=returnHref || "/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"");
  const link=showReturn ? <a href={destination}>{returnLabel}</a> : null;
  return <>
    {withNavigation && link ? <nav aria-label="워크플로우 탐색">{link}</nav> : link}
    <div className="generator-page-identity"><h1 className={embedded ? "embedded-page-title" : undefined}>{title}</h1>{description && <p>{description}</p>}</div>
    <GeneratorChangelog generator={changelog}/>
  </>;
}
