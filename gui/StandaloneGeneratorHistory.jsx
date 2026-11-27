import React,{useEffect,useRef,useState} from 'react';
import GeneratorHistory from './GeneratorHistory.jsx';
import HistoryCleanup from './HistoryCleanup.jsx';
import {validGenerationJobId} from './generationJobId.mjs';
import InvalidHistoryJobNotice from './InvalidHistoryJobNotice.jsx';

/** Shared history state; service adapters own input validation and result rendering. */
export default function StandaloneGeneratorHistory({service,readJob,restore,renderResult}){
  const id=new URLSearchParams(location.search).get('job');
  const [job,setJob]=useState(validGenerationJobId(id)?id:''),[revision,setRevision]=useState(0),[notice,setNotice]=useState('');
  const historyRef=useRef(null),resultRef=useRef(null);
  useEffect(()=>{const details=historyRef.current?.querySelector('details.generator-history');if(details)details.open=true;},[service]);
  function cleaned(message){setJob('');setNotice(message);setRevision(n=>n+1);}
  return <><InvalidHistoryJobNotice/><div ref={historyRef}><GeneratorHistory card allowPriority toggleResult key={service+':'+revision} service={service} readJobWithSignal={readJob} resultId={job} openResult={setJob} onCloseResult={()=>setJob('')} restore={restore} onSelectedDeleted={(id,message)=>{if(job===id)setJob('');setNotice(message);setRevision(n=>n+1);}} footer={<HistoryCleanup allowSelected={false} service={service} onDeleted={cleaned}/>} renderResult={id=>renderResult(id,{resultRef,cleaned})}/></div>{notice && <p role="status">{notice}</p>}</>;
}
