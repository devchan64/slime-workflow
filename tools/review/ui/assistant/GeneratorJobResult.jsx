import React from "react";
import GeneratorJobControls from "./GeneratorJobControls.jsx";
import HistoryCleanup from "./HistoryCleanup.jsx";
import MediaJobResult from "./MediaJobResult.jsx";

export default function GeneratorJobResult({job,service,kind,onDeleted}){
  return job ? <MediaJobResult key={job} kind={kind} service={service} id={job}>
      {(record,refresh)=><React.Fragment key={record?.status || ""}>
        {record && <GeneratorJobControls service={service} id={job} state={record.status} refresh={refresh}/>}
        <HistoryCleanup service={service} job={job} state={record?.status} onDeleted={onDeleted}/>
      </React.Fragment>}
    </MediaJobResult> : <HistoryCleanup service={service} onDeleted={onDeleted}/>;
}
