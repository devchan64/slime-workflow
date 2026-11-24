export function formatGpuQueueSummary(data){
  if(!Array.isArray(data?.jobs) || !data.jobs.every(job=>job && typeof job.id==='string' && job.id.length>0 && typeof job.service==='string' && job.service.length>0) ||
     !['idle','busy','unavailable'].includes(data.gpu_status?.status) || (data.truncated!=null && typeof data.truncated!=='boolean'))
    throw new Error('GPU 대기열 응답을 확인할 수 없습니다.');
  const status={busy:'GPU 사용 중',idle:'GPU 유휴',unavailable:'GPU 상태 확인 불가'}[data.gpu_status.status];
  return {text:status+' · 대기 작업 '+data.jobs.length+'건'+(data.truncated?' 이상':''),unavailable:data.gpu_status.status==='unavailable'};
}
