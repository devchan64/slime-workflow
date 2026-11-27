import React,{useState} from 'react';
import {validGenerationJobId} from './generationJobId.mjs';

export default function InvalidHistoryJobNotice(){
  const params=new URLSearchParams(location.search);
  const [dismissed,setDismissed]=useState(false);
  return !dismissed && params.has('job') && !validGenerationJobId(params.get('job'))
    ? <div role="alert">작업 ID를 확인할 수 없습니다. 이력에서 작업을 다시 선택하세요. <button type="button" onClick={event=>{const article=event.currentTarget.closest('article'),search=article?.querySelector('input[placeholder="ID 일부 입력"]');const target=search && !search.matches(':disabled') ? search : article?.querySelector('details.generator-history > summary');setDismissed(true);target?.focus();}}>안내 닫기</button></div>
    : null;
}
