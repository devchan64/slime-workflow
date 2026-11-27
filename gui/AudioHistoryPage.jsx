import InvalidHistoryJobNotice from './InvalidHistoryJobNotice.jsx';
import React,{useEffect,useRef,useState} from 'react';
import GeneratorHistory from './GeneratorHistory.jsx';
import GeneratorJobResult from './GeneratorJobResult.jsx';
import {untilAborted} from './managementCommand.js';
import {validGenerationJobId} from './generationJobId.mjs';

const services={'sfx-dasheng-audiogen':{label:'효과음',path:'sfx-input'},'music-heartmula':{label:'음악',path:'heartmula-input'}};
export const AUDIO_HISTORY='/management/frame/audio-history/';
export function audioHistoryUrl(service,session,id){const q=new URLSearchParams({service});if(session)q.set('session',session);if(validGenerationJobId(id))q.set('job',id);return AUDIO_HISTORY+'?'+q;}
export default function AudioHistoryPage({service:legacyService}={}){
 const q=new URLSearchParams(location.search),service=legacyService || q.get('service')||'sfx-dasheng-audiogen',profile=Object.hasOwn(services,service) ? services[service] : null,session=q.get('session')||'';
 const [job,setJob]=useState(validGenerationJobId(q.get('job'))?q.get('job'):''),[revision,setRevision]=useState(0),[notice,setNotice]=useState('');const historyRef=useRef(null),resultRef=useRef(null);
 function cleaned(message){setJob('');setNotice(message);setRevision(n=>n+1);}
 async function readJob(id,{signal}={}){const response=await untilAborted(fetch('/management/assistant/'+profile.path+'/'+encodeURIComponent(id),{cache:'no-store',signal}),signal);if(!response.ok)throw Error('저장된 오디오 입력을 확인할 수 없습니다.');const record=await untilAborted(response.json(),signal);if(record?.id!==id || !record.request || typeof record.request!=='object')throw Error('저장된 오디오 입력 형식을 확인할 수 없습니다.');return record;}
 function restore(_input,record){if(!validGenerationJobId(record.id))throw Error('작업 ID를 확인하세요.');const p=new URLSearchParams({restore:record.id});if(session)p.set('session',session);location.assign('/management/frame/'+service+'/?'+p);}
 useEffect(()=>{document.title='오디오 생성이력';const d=historyRef.current?.querySelector('details.generator-history');if(d)d.open=true;},[service]);
 if(!profile)return <article><h1>오디오 생성이력</h1><p role="alert">지원하지 않는 생성기입니다.</p></article>;
 return <article className="generator-page-common"><h1>오디오 생성이력</h1><nav className="generator-section-navigation" aria-label="생성기 페이지 이동"><a href={'/management/frame/'+service+'/'+(session?'?'+new URLSearchParams({session}):'')}>생성기 입력폼</a><span aria-current="page">생성기 생성이력</span></nav><InvalidHistoryJobNotice/><label>생성기 <select value={service} onChange={e=>location.assign(audioHistoryUrl(e.target.value,session))}>{Object.entries(services).map(([id,p])=><option key={id} value={id}>{p.label}</option>)}</select></label><p>선택한 생성기의 이력만 표시합니다.</p><div ref={historyRef}><GeneratorHistory card allowPriority toggleResult key={service+':'+revision} service={service} readJobWithSignal={readJob} resultId={job} openResult={setJob} onCloseResult={()=>setJob('')} restore={restore} onSelectedDeleted={(id,message)=>{if(job===id)setJob('');setNotice(message);setRevision(n=>n+1);}} renderResult={id=><section ref={resultRef} tabIndex={-1} aria-label="선택한 오디오 작업 결과"><GeneratorJobResult selectionControls job={id} service={service} kind="audio" readJobWithSignal={readJob} onDeleted={cleaned}/></section>}/></div>{notice && <p role="status">{notice}</p>}<GeneratorJobResult selectionControls job="" service={service} kind="audio" onDeleted={cleaned}/></article>;
}
