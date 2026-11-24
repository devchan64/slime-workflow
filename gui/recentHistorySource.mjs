export function validRecentHistorySource(source){
  return Boolean(source && typeof source.service==='string' && source.service && typeof source.command==='string' && source.command &&
    (source.result_kind==null || ['audio','video','flux','image','character'].includes(source.result_kind)) &&
    (source.video_result==null || typeof source.video_result==='boolean') &&
    (source.result_path==null || (typeof source.result_path==='string' && /^\/management\/frame\/[a-z0-9-]+\/$/.test(source.result_path))));
}

export function selectRecentHistorySources(sources){
  if(!Array.isArray(sources) || sources.some(source=>!validRecentHistorySource(source)))throw new Error('생성기 목록 형식 오류');
  const eligible=sources.filter(source=>['hermes-generator-source-history','hermes-audio-source-history'].includes(source.command));
  if(!eligible.length)throw new Error('조회할 수 있는 생성기 이력 목록이 없습니다.');
  if(new Set(eligible.map(source=>source.service)).size!==eligible.length)throw new Error('생성기 목록에 중복 항목이 있습니다.');
  return eligible;
}

export function validRecentHistoryPage(page,service){
  return Boolean(page && page.service===service && Array.isArray(page.records) && Number.isSafeInteger(page.unavailable_count) && page.unavailable_count>=0);
}
