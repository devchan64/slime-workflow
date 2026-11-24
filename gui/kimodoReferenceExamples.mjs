export function validKimodoReferenceExamples(data,detail){
  if(!Array.isArray(data))return false;
  if(detail)return data.length>=1 && data.length<=8 && data.every(row=>row && typeof row.name==="string" && row.name && typeof row.data==="string" && row.data);
  const ids=new Set();
  return data.every(row=>{
    if(!row || typeof row.id!=="string" || !row.id || ids.has(row.id) || typeof row.label!=="string")return false;
    ids.add(row.id);return true;
  });
}
