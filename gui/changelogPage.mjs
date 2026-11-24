export function validChangelogPage(result,requestedIndex){
  return Boolean(Number.isSafeInteger(requestedIndex) && requestedIndex>=0 && result &&
    typeof result.content==="string" && Number.isSafeInteger(result.count) && result.count>0 &&
    Number.isSafeInteger(result.index) && result.index===Math.min(requestedIndex,result.count-1) &&
    (result.date===null || typeof result.date==="string"));
}
