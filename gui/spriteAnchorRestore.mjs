export function restoreSpriteAnchors(document,original){
  const {animation,imageSha256}=original;
  if(document.source.animationId!==animation.animationId || document.source.animationVersion!==animation.version ||
    !["anchor","foot-centers","endpoints"].includes(document.coordinateMode))throw new Error("애니메이션 또는 좌표 모드가 일치하지 않습니다.");
  const images=new Set(document.source.sheets.filter(sheet=>sheet.sha256===imageSha256).map(sheet=>sheet.image));
  const frames=document.frames.filter(frame=>images.has(frame.image));
  const byId=new Map(frames.map(frame=>[frame.frameId,frame]));
  if(frames.length!==animation.frames.length || byId.size!==frames.length)throw new Error("원본 이미지 또는 프레임 구성이 변경되었습니다.");
  const feet={};
  const rows=animation.frames.map(({frameId,rect},index)=>{
    const frame=byId.get(frameId);
    if(!frame || ["x","y","width","height"].some(key=>frame.rect[key]!==rect[key]))throw new Error("원본 프레임 영역이 변경되었습니다.");
    if(document.coordinateMode==="foot-centers")feet[index]=frame.points;
    if(document.coordinateMode==="endpoints")feet[index]=[0,2].map(i=>({
      x:(frame.points[i].x+frame.points[i+1].x)/2,y:(frame.points[i].y+frame.points[i+1].y)/2
    }));
    return {...rect,anchorX:frame.anchor.x,anchorY:frame.anchor.y};
  });
  return {rows,feet};
}
