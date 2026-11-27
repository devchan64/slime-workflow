import React from 'react';
import GeneratorHistory from './GeneratorHistory.jsx';
import HistoryCleanup from './HistoryCleanup.jsx';
import MediaJobResult from './MediaJobResult.jsx';
import GeneratorJobControls from './GeneratorJobControls.jsx';
import SavedGeneratorInputs from './SavedGeneratorInputs.jsx';

// The input adapter remains owned by each form: video editing and image-to-video
// have different saved-media formats and validation rules.
export default function MiniMaxVideoHistory({service,job,setJob,revision,setRevision,readJob,readResultInput=readJob,restore,historyRef,resultRef,onNotice,allowPriority=false,resultLabel}){
  function deleted(id,message){if(!id || job===id)setJob('');onNotice(message);setRevision(value=>value+1);}
  return <div ref={historyRef} tabIndex={-1}><GeneratorHistory key={service+':'+revision} service={service} statusCommand="status" card allowPriority={allowPriority} toggleResult readJobWithSignal={readJob} restore={restore} openResult={setJob} resultId={job} onCloseResult={()=>setJob('')} onSelectedDeleted={deleted} footer={<HistoryCleanup service={service} allowSelected={false} onDeleted={message=>deleted('',message)}/>} renderResult={id=><section ref={resultRef} tabIndex={-1} aria-label={resultLabel}><SavedGeneratorInputs id={id} service={service} readJobWithSignal={readResultInput}/><MediaJobResult service={service} id={id}>{(record,reload)=>record && <GeneratorJobControls showActions={false} service={service} id={id} state={record.status} refresh={reload}/>}</MediaJobResult></section>}/></div>;
}
