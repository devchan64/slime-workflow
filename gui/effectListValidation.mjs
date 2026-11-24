export function validEffectList(result){
  if(!result || !Array.isArray(result.effects))return false;
  const ids=new Set();
  return result.effects.every(item=>{
    if(!item || typeof item.id!=="string" || !item.id || ids.has(item.id) || typeof item.name!=="string" || !item.name)return false;
    ids.add(item.id);return true;
  });
}
