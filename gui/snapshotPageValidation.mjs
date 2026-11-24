export function validSnapshotPage(result,cursor,{field,limit,validItem}){
  if(!result || !Array.isArray(result[field]) || !Number.isSafeInteger(result.total) || result.total<0 || !Number.isSafeInteger(result.offset) || result.offset!==(cursor.offset ?? 0) || typeof result.snapshot!=="string" || !/^[a-f0-9]{64}$/.test(result.snapshot) || (cursor.snapshot && cursor.snapshot!==result.snapshot))return false;
  const items=result[field];
  if(items.length!==Math.min(limit,Math.max(0,result.total-result.offset)))return false;
  const next=result.offset+items.length;
  if(result.next_offset!==(next<result.total ? next : null))return false;
  const ids=new Set();
  return items.every(item=>{
    if(!item || typeof item.id!=="string" || !item.id || ids.has(item.id) || !validItem(item))return false;
    ids.add(item.id);return true;
  });
}
