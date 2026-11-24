export function validEffectDetail(value,id){
  const document=value?.document;
  if(document?.id!==id || typeof document.name!=="string" || typeof document.renderer!=="string" || !Number.isInteger(document.frames) || document.frames<1 || typeof value.revision!=="string" || !value.revision || typeof value.sheetImage!=="string" || !value.sheetImage || typeof value.rendererModule!=="string" || (value.hostImage!=null && typeof value.hostImage!=="string"))return false;
  if(document.renderer==="waypoint-animation")return true;
  const alignment=document.alignment;
  const rectangle=row=>Array.isArray(row) && row.length===4 && row.every(Number.isFinite);
  return Boolean(alignment && typeof alignment.texture==="string" && Number.isFinite(alignment.alpha) && rectangle(alignment.target) && Array.isArray(alignment.frames) && alignment.frames.length===8 && alignment.frames.every(rectangle));
}

export function validWaypointFrames(frames,count){
  return Array.isArray(frames) && frames.length===count && count>0 && frames.every(frame=>frame && frame.rect && frame.anchor && ["x","y","width","height"].every(key=>Number.isFinite(frame.rect[key])) && frame.rect.width>0 && frame.rect.height>0 && ["x","y"].every(key=>Number.isFinite(frame.anchor[key])));
}
