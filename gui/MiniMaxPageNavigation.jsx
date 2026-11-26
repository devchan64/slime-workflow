import React,{useEffect,useState} from 'react';

export function useMiniMaxPages(enabled){
  const initial=()=>{const q=new URLSearchParams(location.search);return q.get('view')==='history' || q.has('job') ? 'history' : 'input';};
  const [page,setPage]=useState(initial);
  useEffect(()=>{if(!enabled)return;const onPop=()=>setPage(initial());window.addEventListener('popstate',onPop);return ()=>window.removeEventListener('popstate',onPop);},[enabled]);
  function navigate(next,id){const url=new URL(location.href);url.searchParams.delete('view');url.searchParams.delete('job');if(next==='history')url.searchParams.set('view','history');if(id)url.searchParams.set('job',id);url.hash=id ? 'job-result' : '';history.pushState({},'',url);setPage(next);}
  return {page,navigate};
}
export function MiniMaxPageNavigation({page,navigate,locked,reviewHref}){
  return <nav className="generator-section-navigation" aria-label="생성기 페이지 이동"><button type="button" aria-current={page==='input' ? 'page' : undefined} disabled={locked} onClick={()=>navigate('input')}>생성기 입력폼</button><button type="button" aria-current={page==='history' ? 'page' : undefined} disabled={locked} onClick={()=>navigate('history')}>생성기 생성이력</button>{reviewHref && <a href={reviewHref}>건물 검수 페이지</a>}{locked && <small>요청 확인을 마치거나 입력 수정으로 돌아간 뒤 이동하세요.</small>}</nav>;
}
