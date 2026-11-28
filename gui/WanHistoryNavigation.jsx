import React from 'react';
import {validVideoJobId} from './videoJobId.mjs';
export const WAN_HISTORY_SERVICES=Object.freeze({'wan22-i2v':'I2V','wan22-vace':'VACE','wan22-fun-control':'Fun Control','wan22-animate2':'Animate-2'});
export function wanHistoryUrl(service,session,id){if(!Object.hasOwn(WAN_HISTORY_SERVICES,service))throw Error('지원하지 않는 생성기입니다.');const q=new URLSearchParams();if(session)q.set('session',session);if(validVideoJobId(id))q.set('job',id);return '/management/frame/'+service+'-history/'+(q.size?'?'+q:'');}
export default function WanHistoryNavigation({service,session}){return <nav className="generator-section-navigation" aria-label="생성기 페이지 이동"><a href={'/management/frame/'+service+'-generator/'+(session?'?'+new URLSearchParams({session}):'')}>생성기 입력폼</a><span aria-current="page">생성기 생성이력</span></nav>;}
