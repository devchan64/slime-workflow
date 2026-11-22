export function validSessionListPage(page,request){
  if(!page || !Array.isArray(page.sessions) || page.sessions.length>30 ||
    page.sessions.some(row=>!row || !/^[a-f0-9]{32}$/.test(row.id || "") ||
      (row.title!=null && typeof row.title!=="string") || typeof row.updated_at!=="string") ||
    new Set(page.sessions.map(row=>row.id)).size!==page.sessions.length ||
    !Number.isInteger(page.total) || page.total<0 || page.offset!==request.offset ||
    page.offset+page.sessions.length>page.total || !/^[a-f0-9]{64}$/.test(page.snapshot || "") ||
    (request.snapshot && page.snapshot!==request.snapshot))return false;
  const next=page.offset+page.sessions.length;
  return page.next_offset===null ? next===page.total :
    Number.isInteger(page.next_offset) && page.sessions.length>0 && page.next_offset===next && next<page.total;
}
