export function validMapDraftPreview(value){
  return Boolean(value && typeof value.changed==="boolean" && typeof value.save_available==="boolean" && /^[a-f0-9]{64}$/.test(value.token || "") && value.render && typeof value.render==="object" && !Array.isArray(value.render) && ["cells","reachable"].every(key=>Number.isInteger(value[key]) && value[key]>=0) && (value.save_block_reason==null || typeof value.save_block_reason==="string"));
}

export function isMapCellDirty(cell,original){
  if(!cell || !original)return false;
  const height=String(cell.height ?? ""),originalHeight=String(original.height ?? "");
  const sameHeight=height.trim()!=="" && originalHeight.trim()!=="" && Number.isFinite(Number(height)) && Number(height)===Number(originalHeight);
  return ["tile","blocked","wall"].some(key=>String(cell[key] ?? "")!==String(original[key] ?? "")) || (!sameHeight && height!==originalHeight);
}

export function invalidMapCellHeight(value){
  return value==null || String(value).trim()==="" || !Number.isInteger(Number(value)) || Number(value)<0 || Number(value)>20;
}

export function readMapCell(snapshot,map,position){
  if(snapshot?.map!==map || typeof snapshot.revision!=="string" || !Array.isArray(snapshot.tiles?.rows) || !Array.isArray(snapshot.tiles?.objects) || !Array.isArray(snapshot.terrain?.elevations) || !Array.isArray(snapshot.terrain?.blocked) || snapshot.terrain.blocked.some(item=>!Array.isArray(item) || item.length!==2 || !item.every(Number.isInteger)) || !snapshot.codes || typeof snapshot.codes!=="object")throw new Error("지도 원본 응답 형식을 확인할 수 없습니다.");
  const column=position?.column,row=position?.row;
  if(!Number.isInteger(column) || !Number.isInteger(row) || row<0 || column<0 || row>=snapshot.tiles.rows.length || typeof snapshot.tiles.rows[row]!=="string" || column>=snapshot.tiles.rows[row].length || !Array.isArray(snapshot.terrain.elevations[row]) || column>=snapshot.terrain.elevations[row].length)throw new Error("지도 범위 안의 정수 열·행을 선택하세요.");
  const tile=snapshot.tiles.rows[row][column],height=snapshot.terrain.elevations[row][column];
  if(!Object.hasOwn(snapshot.codes,tile) || !Number.isInteger(height))throw new Error("선택한 셀의 원본 정보를 확인할 수 없습니다.");
  return {column,row,tile,height,blocked:snapshot.terrain.blocked.some(([x,y])=>x===column && y===row)};
}

export function mapDraftSaveReason(value){
  if(!validMapDraftPreview(value))return "초안 검증 결과를 다시 확인하세요.";
  if(!value.changed)return "변경된 내용이 없습니다. 초안을 수정한 뒤 다시 검증하세요.";
  if(!value.save_available){
    if(value.save_block_reason==="database")return "현재 데이터베이스 저장 경로에서는 이 화면에서 저장할 수 없습니다. 초안을 내려받아 보관하세요.";
    if(value.save_block_reason==="interrupted")return "이전 지도 저장의 복구가 필요합니다. 운영자에게 저장 상태 확인을 요청하세요.";
    return "지도 저장 가능 상태를 확인할 수 없습니다. 운영자에게 확인을 요청하세요.";
  }
  return "";
}
