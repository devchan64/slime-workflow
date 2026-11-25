export function validWorldMap(data){
  if(!Array.isArray(data?.maps))return false;
  const ids=new Set();
  for(const map of data.maps){
    if(!map || typeof map.id!=="string" || !map.id.trim() || ids.has(map.id) || typeof map.name!=="string" || !map.name.trim() || typeof map.safeTown!=="boolean" || !Number.isSafeInteger(map.column) || !Number.isSafeInteger(map.row) || !map.thumbnail || ["url","managementId","version","sha256","path"].some(key=>typeof map.thumbnail[key]!=="string") || !Array.isArray(map.connections))return false;
    ids.add(map.id);
  }
  return data.maps.every(map=>map.connections.every(edge=>edge && ["id","target","direction"].every(key=>typeof edge[key]==="string") && (edge.targetWaypointId==null || typeof edge.targetWaypointId==="string") && ids.has(edge.target)));
}

export function worldMapDirectionLabel(direction){
  const labels={north:"북쪽",south:"남쪽",east:"동쪽",west:"서쪽"};
  return Object.hasOwn(labels,direction) ? labels[direction] : direction;
}

// 지도 사이의 연결을 한 번만 그린다. 방향별 웨이포인트는 상세 표에 그대로 표시한다.
export function worldMapLinks(maps){
  const seen=new Set(),links=[];
  for(const map of maps)for(const edge of map.connections){
    const pair=[map.id,edge.target].sort();
    const key=JSON.stringify(pair);
    if(!seen.has(key)){seen.add(key);links.push(pair);}
  }
  return links;
}
