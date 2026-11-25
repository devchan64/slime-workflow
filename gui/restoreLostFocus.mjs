/** 비동기 처리 중 초점이 문서 본문으로 사라진 경우에만 지정한 대상으로 옮긴다. */
export function restoreLostFocus(document,target) {
  if(document.activeElement!==document.body || !target?.isConnected || target.disabled)return false;
  target.focus();
  return true;
}

/** 접힌 details 안의 대상은 화면에서 보이는 바깥쪽 접기 제목으로 대체한다. */
export function visibleFocusTarget(target) {
  let visible=target;
  for(let node=target;node;node=node.parentElement) {
    if(node.tagName==='DETAILS' && !node.open) visible=node.querySelector(':scope > summary') || visible;
  }
  return visible;
}
