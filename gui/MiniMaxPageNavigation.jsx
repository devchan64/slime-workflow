import React from 'react';

export function MiniMaxPageNavigation({navigate,locked,reviewHref,historyHref}){
  return <nav className="generator-section-navigation" aria-label="생성기 페이지 이동"><span aria-current="page">생성기 입력폼</span>{historyHref && !locked ? <a href={historyHref} target="_blank" rel="noopener">생성기 생성이력 (새 탭)</a> : <button type="button" disabled={locked} onClick={()=>navigate('history')}>생성기 생성이력</button>}{reviewHref && <a href={reviewHref}>건물 검수 페이지</a>}{locked && <small>요청 확인을 마치거나 입력 수정으로 돌아간 뒤 이동하세요.</small>}</nav>;
}
