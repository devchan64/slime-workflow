export function validInferenceCompletion(value){
  return typeof value==='string' && /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && !Number.isNaN(Date.parse(value));
}

/** 공용 진행 UI가 표시할 실제 단계 관측을 정규화한다. */
export function observedGenerationProgress(job){
  const event=job?.progress_event;
  const worker=job?.worker_progress;
  const eventEstimate=event && typeof event['generation.estimate.basis']==='string' && event['generation.estimate.basis'].trim() && typeof event['generation.estimate.scope']==='string' && event['generation.estimate.scope'].trim() && Number.isSafeInteger(event['generation.estimate.sample_count']) && event['generation.estimate.sample_count']>=0 ? {remaining:event['generation.estimate.remaining_seconds'],completion:event['generation.estimate.completion_time'],basis:event['generation.estimate.basis'],samples:event['generation.estimate.sample_count'],scope:event['generation.estimate.scope']} : null;
  const candidates=[event && {stage:event['generation.stage'],step:event['generation.step'],total:event['generation.step.total'],updatedAt:event['generation.updated_at'],scope:'추론 단계; 전체 작업 진행률과 별개',estimate:eventEstimate},worker && {stage:worker.stage,step:worker.step,total:worker.total,updatedAt:worker.updated_at,scope:worker.scope}];
  return candidates.find(value=>value && typeof value.stage==='string' && value.stage && Number.isInteger(value.step) && Number.isInteger(value.total) && value.total>0 && value.step>=0 && value.step<=value.total && typeof value.updatedAt==='string') || null;
}
