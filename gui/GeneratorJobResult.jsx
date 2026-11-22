import React from "react";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import MediaJobResult from "./MediaJobResult.jsx";
import SavedGeneratorInputs from "./SavedGeneratorInputs.jsx";

export default function GeneratorJobResult({job,service,kind,onDeleted,controls=true,selectionControls=false,readJob,statusCommand}){
  return job ? <><SavedGeneratorInputs key={'input:'+job} id={job} service={service} readJob={readJob} statusCommand={statusCommand}/><MediaJobResult key={job} kind={kind} service={service} id={job}>
      {(record,refresh)=><React.Fragment key={record?.status || ""}>
        {controls && record && <GeneratorJobControls service={service} id={job} state={record.status} refresh={refresh} showActions={!selectionControls}/>}
        <HistoryCleanup service={service} job={job} state={record?.status} onDeleted={onDeleted} allowSelected={!selectionControls}/>
      </React.Fragment>}
    </MediaJobResult></> : <HistoryCleanup service={service} onDeleted={onDeleted} allowSelected={!selectionControls}/>;
}
