import React,{useState} from 'react';

function MediaThumbnail({item}){const [failed,setFailed]=useState(!item.src),[fallback,setFallback]=useState(false);const thumbnail=/^\/management\/assistant\/(?:animate-input\/\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}\/motion|vace-input\/\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}\/(?:pose_video|edit_video|edit_mask))$/.test(item.src) ? item.src+'-thumbnail' : /^\/management\/assistant\/fun-pose\/\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(item.src) ? item.src.replace('/fun-pose/','/fun-pose-thumbnail/') : '';return <figure>{failed ? <span role="status">미리보기를 불러올 수 없습니다.</span> : item.type==='image' || fallback ? <img src={fallback ? thumbnail : item.src} alt={item.label} onError={()=>setFailed(true)}/> : <video src={item.src} preload="metadata" muted playsInline aria-label={item.label} onError={()=>thumbnail ? setFallback(true) : setFailed(true)}/>}<figcaption>{item.label}</figcaption></figure>;}

import {historyInputDetails,historyInputSummary} from './historyInputSummary.mjs';

/** 저장 입력은 읽기 전용으로 표시하고 첨부 데이터는 미디어 미리보기로 표시한다. */
export default function HistoryInputPreview({request,service}){
  const summary=historyInputSummary(request,service);
  const prompts=[['user_prompt','사용자 프롬프트'],['prompt','프롬프트'],['negative_prompt','부정 프롬프트'],['translation_source_ko','번역 원문']].filter(([key])=>typeof request[key]==='string' && request[key].trim());
  const media=[];
  if(Array.isArray(request.images))request.images.forEach((value,index)=>{if(typeof value==='string' && value)media.push({label:`참조 이미지 ${index+1}`,src:value.startsWith('data:image/') || /^\/management\/assistant\/(?:animate-input|vace-input)\/\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}\/reference$/.test(value) ? value : value.startsWith('iVBORw0KGgo') || value.startsWith('/9j/') ? `data:${value.startsWith('/9j/') ? 'image/jpeg' : 'image/png'};base64,${value}` : '',type:'image'});});
  for(const [key,label] of [['edit_video','원본 영상'],['driving_video','동작 영상'],['pose_video','포즈 영상'],['edit_mask','마스크 영상']]){
    const value=request[key];
    if(typeof value!=='string' || !value)continue;
    const trustedPath=/^\/management\/assistant\/(?:animate-input\/\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}\/motion|vace-input\/\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}\/(?:pose_video|edit_video|edit_mask)|fun-pose\/\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8})$/.test(value);
    const videoData=value.length>100 && /^[A-Za-z0-9+/=]+$/.test(value);
    const src=value.startsWith('data:video/') || trustedPath ? value : videoData ? `data:video/mp4;base64,${value}` : '';
    media.push({label,src,type:'video'});
  }
  return <><strong>저장된 입력</strong>{summary.length>0 && <p>{summary.join(' · ')}</p>}{prompts.map(([key,label])=><div key={key}><strong>{label}</strong><pre>{request[key]}</pre></div>)}{media.length>0 && <div className="history-input-media" aria-label="입력 미디어">{media.map(item=><MediaThumbnail key={item.label} item={item}/>)}</div>}<section aria-label="입력 설정 상세"><strong>입력 설정 상세</strong><pre>{historyInputDetails(request)}</pre></section></>;
}
