const optionalString=value=>value==null || typeof value==='string';

export function validSessionQueueResult(value){
  if(!value || !Array.isArray(value.steps) || (value.direct_jobs!=null && !Array.isArray(value.direct_jobs)))return false;
  const validCommon=row=>row && typeof row==='object' && !Array.isArray(row) && optionalString(row.generator) && typeof row.state==='string' && typeof row.request_id==='string' && optionalString(row.source_job_id) && optionalString(row.created_at) && optionalString(row.observed_at);
  return value.steps.every(row=>validCommon(row) && typeof row.run_id==='string' && typeof row.step_id==='string' && optionalString(row.source_state)) &&
    (value.direct_jobs || []).every(row=>validCommon(row) && optionalString(row.source_kind) && optionalString(row.proposal_job_id) && optionalString(row.form_id) && optionalString(row.message_snapshot));
}

export function sessionQueueStateLabel(states,state){
  return typeof state==='string' && Object.hasOwn(states,state) ? states[state] : typeof state==='string' && state ? state : '확인 불가';
}
