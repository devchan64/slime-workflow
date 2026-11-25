export function validEffectList(result){
  if(!result || !Array.isArray(result.effects))return false;
  const ids=new Set();
  return result.effects.every(item=>{
    if(!item || typeof item.id!=="string" || !item.id.trim() || ids.has(item.id) || typeof item.name!=="string" || !item.name.trim())return false;
    ids.add(item.id);return true;
  });
}
