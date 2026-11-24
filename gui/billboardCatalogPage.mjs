export function validBillboardCatalogPage(result,request) {
  if(!result || !Array.isArray(result.items) || !Number.isSafeInteger(result.total) || result.total<0 || !Number.isSafeInteger(result.offset) || result.offset!==request.offset || !Number.isSafeInteger(result.limit) || result.limit!==request.limit || result.limit<1 || result.items.length>result.limit)return false;
  const next=result.offset+result.limit<result.total ? result.offset+result.limit : null;
  if(result.next_offset!==next || result.items.length!==Math.min(result.limit,Math.max(0,result.total-result.offset)))return false;
  const ids=new Set();
  return result.items.every(item=>{
    if(!item || typeof item.id!=="string" || !item.id || ids.has(item.id) || typeof item.name!=="string" || typeof item.category!=="string" || !item.modeling || typeof item.modeling!=="object" || Array.isArray(item.modeling) || !Array.isArray(item.maps))return false;
    ids.add(item.id);
    if(["purpose","composition"].some(key=>item.modeling[key]!=null && typeof item.modeling[key]!=="string"))return false;
    return item.maps.every(map=>map && typeof map.map==="string" && typeof map.source_path==="string" && (map.occurrences==null || Number.isSafeInteger(map.occurrences) && map.occurrences>=0));
  });
}

export function billboardCategoryLabel(categories,category) {
  return Object.hasOwn(categories,category) ? categories[category] : "분류 확인 불가";
}
