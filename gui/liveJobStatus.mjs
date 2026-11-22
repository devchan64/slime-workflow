export function liveJobStatus(job){return !job || ['queued','running'].includes(job.status);}
