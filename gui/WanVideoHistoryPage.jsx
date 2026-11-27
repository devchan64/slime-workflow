import InvalidHistoryJobNotice from './InvalidHistoryJobNotice.jsx';
import WanHistoryNavigation,{wanHistoryUrl} from "./WanHistoryNavigation.jsx";
import VaceHistoryPage from "./VaceHistoryPage.jsx";
import FunControlHistoryPage from "./FunControlHistoryPage.jsx";
import AnimateHistoryPage from "./AnimateHistoryPage.jsx";
import React,{useEffect,useRef,useState} from 'react';
import VideoHistory from './MiniMaxVideoHistory.jsx';
import {untilAborted} from './managementCommand.js';
import {validVideoJobId} from './videoJobId.mjs';

const service='wan22-i2v';
export function wanVideoHistoryUrl(session,id){return wanHistoryUrl(service,session,id);}
export default function WanVideoHistoryPage(){const requested=new URLSearchParams(location.search).get('service')||service;const pages={'wan22-i2v':WanI2VHistoryPage,'wan22-vace':VaceHistoryPage,'wan22-fun-control':FunControlHistoryPage,'wan22-animate2':AnimateHistoryPage};const Page=Object.hasOwn(pages,requested) ? pages[requested] : null;return Page ? <Page key={requested}/> : <article><h1>Wan 영상 생성이력</h1><p role="alert">지원하지 않는 생성기입니다.</p></article>;}
export function WanI2VHistoryPage(){
 const q=new URLSearchParams(location.search),session=q.get('session')||'';
 const [job,setJob]=useState(validVideoJobId(q.get('job'))?q.get('job'):''),[revision,setRevision]=useState(0),[notice,setNotice]=useState('');const historyRef=useRef(null),resultRef=useRef(null);
 async function readJob(id,{signal}={}){const response=await untilAborted(fetch('/management/assistant/wan22-i2v-input/'+encodeURIComponent(id),{cache:'no-store',signal}),signal);if(!response.ok)throw Error('저장 입력을 불러오지 못했습니다. 참조 이미지와 현재 지원되는 설정을 확인한 뒤 다시 시도하세요.');const record=await untilAborted(response.json(),signal);if(record?.id!==id || !record.request || !Array.isArray(record.request.images) || record.request.images.length!==1 || typeof record.request.images[0]!=='string')throw Error('저장 입력 형식을 확인할 수 없습니다.');return record;}
 function restore(_request,record){if(!validVideoJobId(record.id))throw Error('작업 ID를 확인하세요.');const q=new URLSearchParams({restore:record.id});if(session)q.set('session',session);location.assign('/management/frame/wan22-i2v-generator/?'+q);}
 useEffect(()=>{document.title='Wan 영상 생성이력';const d=historyRef.current?.querySelector('details.generator-history');if(d)d.open=true;},[]);
 return <article className="vace-page generator-page-common vace-standalone"><h1>Wan 2.2 I2V 생성이력</h1><WanHistoryNavigation service={service} session={session}/>{notice && <p role="status">{notice}</p>}<InvalidHistoryJobNotice/><VideoHistory service={service} job={job} setJob={setJob} revision={revision} setRevision={setRevision} readJob={readJob} restore={restore} historyRef={historyRef} resultRef={resultRef} onNotice={setNotice} allowPriority resultLabel="선택한 영상 작업 결과"/></article>;
}
