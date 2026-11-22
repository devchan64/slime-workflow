// SQLite CURRENT_TIMESTAMP returns UTC without a timezone suffix.
export function parseSessionTime(value) {
  if (typeof value !== 'string' || !value) return NaN;
  const normalized = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(value)
    ? value.replace(' ', 'T') + 'Z' : value;
  return Date.parse(normalized);
}

// Missing or malformed timestamps remain at the end in their original order.
export function newestSessionJobs(rows) {
  return rows.map((row,index)=>({row,index,time:parseSessionTime(row.step.created_at)}))
    .sort((a,b)=>(Number.isFinite(b.time) ? b.time : -Infinity)-(Number.isFinite(a.time) ? a.time : -Infinity) || a.index-b.index)
    .map(({row})=>row);
}
