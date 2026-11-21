import React,{useState} from "react";
import GeneratorHistory from "./GeneratorHistory.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import {managementCommand} from "./managementCommand.js";

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
    const history=await managementCommand(service,"history",{});
    return history.records.find(record=>record.id===job) || {};
  }
  return <main><article><a href={"/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화로 돌아가기</a>
    <h1>Qwen 이미지 생성 이력</h1><p>{service} · 보관된 작업</p>
    <GeneratorHistory service={service} readJob={readJob} inspectResult={record=>select(record.id)} openResult={select}/>
    {id && <ArchiveDetail key={id} service={service} id={id}/>}
  </article></main>;
}
