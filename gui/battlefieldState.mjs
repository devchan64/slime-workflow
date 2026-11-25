export function validBattlefieldState(value){
  if(!value || !Array.isArray(value.choices) || !value.choices.length || typeof value.field!=="string" || typeof value.status!=="string" || typeof value.cameraReady!=="boolean" || typeof value.spawnRegionsVisible!=="boolean")return false;
  const ids=new Set();
  for(const row of value.choices){
    if(!Array.isArray(row) || row.length!==2 || typeof row[0]!=="string" || !row[0].trim() || typeof row[1]!=="string" || !row[1].trim() || ids.has(row[1]))return false;
    ids.add(row[1]);
  }
  return ids.has(value.field);
}

export function battlefieldLoadFailed(value){
  return validBattlefieldState(value) && value.status.startsWith("전장 로드 실패:");
}

export function sameBattlefieldState(previous,next){
  if(!validBattlefieldState(previous) || !validBattlefieldState(next))return false;
  if(["field","status","cameraReady","spawnRegionsVisible"].some(key=>previous[key]!==next[key]) || previous.choices.length!==next.choices.length)return false;
  return previous.choices.every((row,index)=>row[0]===next.choices[index][0] && row[1]===next.choices[index][1]);
}
