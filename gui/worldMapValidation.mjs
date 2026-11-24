export function validWorldMap(data){
  if(!Array.isArray(data?.maps))return false;
  const ids=new Set();
  for(const map of data.maps){
    if(!map || typeof map.id!=="string" || !map.id || ids.has(map.id) || typeof map.name!=="string" || typeof map.safeTown!=="boolean" || !Number.isSafeInteger(map.column) || !Number.isSafeInteger(map.row) || !map.thumbnail || ["url","managementId","version","sha256","path"].some(key=>typeof map.thumbnail[key]!=="string") || !Array.isArray(map.connections))return false;
    ids.add(map.id);
  }
  return data.maps.every(map=>map.connections.every(edge=>edge && ["id","target","direction"].every(key=>typeof edge[key]==="string") && (edge.targetWaypointId==null || typeof edge.targetWaypointId==="string") && ids.has(edge.target)));
}
