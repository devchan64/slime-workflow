/** 비동기 처리 중 초점이 문서 본문으로 사라진 경우에만 지정한 대상으로 옮긴다. */
export function restoreLostFocus(document,target) {
  if(document.activeElement!==document.body || !target?.isConnected || target.disabled)return false;
  target.focus();
  return true;
}
