export function duplicateKeyframeFrames(rows){
  const seen=new Set(),duplicates=new Set();
  for(const row of rows){
    if(typeof row.frame==="string" && !row.frame.trim())continue;
    const frame=Number(row.frame);
    if(!Number.isSafeInteger(frame) || frame<1)continue;
    if(seen.has(frame))duplicates.add(frame);else seen.add(frame);
  }
  return duplicates;
}
