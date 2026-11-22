import React,{useState} from "react";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import {managementCommand} from "./managementCommand.js";

import {readArchiveJob} from "./readArchiveJob.mjs";

function ArchiveDetail({service,id}){
  const [log,setLog]=useState(null),[error,setError]=useState("");
  async function readLog(){
    try{
      const result=await managementCommand(service,"logs",{id});
      setLog(result.log || "기록된 로그가 없습니다.");setError("");
    }catch(problem){setError(problem.message);}
  }
  return <><MediaJobResult service={service} kind="image" id={id}/>
    <button onClick={readLog}>실행 로그 조회</button>
    {log!==null && <pre>{log}</pre>}{error && <p role="alert">{error}</p>}</>;
}

export default function QwenArchive(){
  const params=new URLSearchParams(location.search);
  const service=params.get("service"),session=params.get("session");
  const [id,select]=useState(params.get("job") || "");
  async function readJob(job){
    return readArchiveJob(managementCommand,service,job);
  }
  return <main className="single-generator-shell"><article className="single-generator-page"><a href={"/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화로 돌아가기</a>
    <h1>Qwen 이미지 생성 이력</h1><p>{service} · 보관된 작업</p>
    <GeneratorChangelog generator={service}/>
    <GeneratorHistory service={service} readJob={readJob} inspectResult={record=>select(record.id)} openResult={select}/>
    {id && <ArchiveDetail key={id} service={service} id={id}/>}
  </article></main>;
}
