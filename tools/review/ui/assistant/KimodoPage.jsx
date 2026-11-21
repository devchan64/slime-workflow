import KimodoGeneration from "./KimodoGeneration.jsx";
import React from "react";
import ModelReadiness from "./ModelReadiness.jsx";
import DownloadProgress from "./DownloadProgress.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import {HistoryPage} from "./SourceHistory.jsx";

export default function KimodoPage(){
  const session=new URLSearchParams(location.search).get("session") || "";
  const conversation="/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"");
  function choose(label,value){
    const key="hermes-draft-"+session;
    sessionStorage.setItem(key,[sessionStorage.getItem(key),label+" "+value].filter(Boolean).join("\n"));
    location.assign(conversation);
  }
  return <main><article><a href={conversation}>헤르메스 대화로 돌아가기</a>
    <h1>Kimodo 모션 생성기</h1>
    <GeneratorChangelog generator="kimodo-generator"/>
    <ModelReadiness service="kimodo" manage/><DownloadProgress service="kimodo"/>
    <KimodoGeneration session={session}/>
    <h2>생성 이력</h2>
    <HistoryPage source={{service:"kimodo",command:"hermes-generator-source-history"}} session={session} choose={choose}/>
  </article></main>;
}
