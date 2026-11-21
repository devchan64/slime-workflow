const services = new Set(['wan22-fun-control','wan22-vace','wan22-animate2','dwpose','kimodo']);

// An assistant response is data: recognize only one complete, read-only lookup example.
export function videoLookupSuggestion(answer,userText){
  if(typeof answer!=="string" || typeof userText!=="string")return null;
  const match=answer.match(/^[^`\n]{1,300}\n\s*```(?:bash|sh)?\s*\n\/runtime\/\.venv\/bin\/python\s+\/control\/management-status\.py\s+video-source-status\s+'([^'\n]+)'\s*\n```\s*$/);
  if(!match)return null;
  try{
    const value=JSON.parse(match[1]);
    if(!value || Array.isArray(value) || Object.keys(value).sort().join(',')!=='job_id,service' ||
       !services.has(value.service) || typeof value.job_id!=='string' ||
       !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(value.job_id) || !userText.includes(value.job_id))return null;
    return value;
  }catch{return null;}
}
