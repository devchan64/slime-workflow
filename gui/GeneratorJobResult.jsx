import React from "react";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import SavedGeneratorInputs from "./SavedGeneratorInputs.jsx";

export default function GeneratorJobResult({job,service,kind,onDeleted,controls=true,selectionControls=false,readJob,readJobWithSignal,statusCommand}){
  return job ? <><SavedGeneratorInputs key={'input:'+job} id={job} service={service} readJob={readJob} readJobWithSignal={readJobWithSignal} statusCommand={statusCommand}/><MediaJobResult key={job} kind={kind} service={service} id={job} inGenerator>
      {(record,refresh,{stale})=><React.Fragment key={record?.status || ""}>
        {stale && <p role="status">작업 상태를 다시 조회할 때까지 이 작업의 제어와 삭제를 사용할 수 없습니다.</p>}
        {controls && record && <GeneratorJobControls service={service} id={job} state={record.status} refresh={refresh} disabled={stale} showActions={!selectionControls}/>}
        {!selectionControls && <HistoryCleanup service={service} job={job} state={stale ? null : record?.status} onDeleted={onDeleted}/>}
      </React.Fragment>}
    </MediaJobResult></> : <HistoryCleanup service={service} onDeleted={onDeleted} allowSelected={!selectionControls}/>;
}
