export function validKeyframeBatchRequest(rows,frameCount){
  if(!Number.isSafeInteger(frameCount) || frameCount<1 || !Array.isArray(rows) || rows.length<1 || rows.length>20)return false;
  const frames=new Set();
  return rows.every(row=>{
    if(!row || typeof row.id!=="string" || !/^[a-f0-9]{32}$/.test(row.id) || !Number.isSafeInteger(row.frame) || row.frame<1 || row.frame>frameCount || frames.has(row.frame))return false;
    frames.add(row.frame);return true;
  });
}

export function validKeyframeBatchResult(result,expected){
  if(!result || !Array.isArray(result.placements) || result.placements.length!==expected.length || result.placements.some((row,index)=>!row || row.id!==expected[index].id || row.frame!==expected[index].frame) || typeof result.note!=="string" || !/^[a-f0-9]{64}$/.test(result.skeleton_signature_sha256 || "") || !Array.isArray(result.sources))return false;
  const needed=new Set(expected.map(row=>row.id)),seen=new Set();
  if(result.sources.length!==needed.size)return false;
  return result.sources.every(source=>{
    if(!source || typeof source.id!=="string" || !needed.has(source.id) || seen.has(source.id) || typeof source.preview_sha256!=="string" || !/^[a-f0-9]{64}$/.test(source.preview_sha256) || typeof source.source_sha256!=="string" || !/^[a-f0-9]{64}$/.test(source.source_sha256))return false;
    seen.add(source.id);return true;
  });
}
