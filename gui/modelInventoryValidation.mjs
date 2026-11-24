export function validModelInventory(model){
  if(!model || !Array.isArray(model.files) || !Number.isSafeInteger(model.count) || model.count<model.files.length ||
     !Number.isSafeInteger(model.total_bytes) || model.total_bytes<0 || typeof model.truncated!=="boolean" ||
     typeof model.incomplete!=="boolean" || model.truncated!==(model.count>model.files.length) ||
     !model.files.every(file=>file && typeof file.path==="string" && file.path.length>0 && Number.isSafeInteger(file.bytes) && file.bytes>=0) ||
     new Set(model.files.map(file=>file.path)).size!==model.files.length)return false;
  const listedBytes=model.files.reduce((sum,file)=>sum+file.bytes,0);
  return Number.isSafeInteger(listedBytes) && (model.truncated ? listedBytes<=model.total_bytes : listedBytes===model.total_bytes);
}
