export function formatActivityCopy(start,result,label){
  const event=start || result || {};
  const lines=[`도구 활동: ${event.name || '알 수 없음'}`,`상태: ${label || '확인 불가'}`];
  if(event.timestamp)lines.push(`시각: ${event.timestamp}`);
  if(start?.target)lines.push('', '실행 대상:',start.target);
  if(result)lines.push('', '도구 결과:',typeof result.output==='string' ? result.output : '상세 출력 없음',...(result.output_truncated ? ['(출력은 앞부분만 표시됨)'] : []));
  else lines.push('', '도구 결과: 아직 기록되지 않음');
  if(Number.isInteger(result?.duration_ms))lines.push('',`소요 시간: ${(result.duration_ms/1000).toFixed(1)}초`);
  if(event.call_id)lines.push(`호출 ID: ${event.call_id}`);
  return lines.join('\n');
}
