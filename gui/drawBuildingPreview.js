import {startImageLoadDeadline} from "./imageLoadDeadline.mjs";

export function drawBuildingPreview(canvas,preview,placement,values,onStatus=()=>{},options={}){
  const {anchorX,anchorY,displayWidthAdjustment:widthAdjustment,displayHeightAdjustment:heightAdjustment,
    shadowShape:currentShadowShape,shadowOffsetColumn:currentShadowColumnOffset,shadowOffsetRow:currentShadowRowOffset,
    shadowScaleX:currentShadowColumnScale,shadowScaleY:currentShadowRowScale}=values;
 const ctx=canvas.getContext('2d');const img=new Image();
 const ticket=(canvas.__buildingPreviewTicket||0)+1;canvas.__buildingPreviewTicket=ticket;
 ctx.clearRect(0,0,canvas.width,canvas.height);
 onStatus("loading");
 let active=true;
 const cancelTimeout=startImageLoadDeadline(()=>{if(active && canvas.__buildingPreviewTicket===ticket){img.onload=null;img.onerror=null;onStatus("image-error");}});
 img.onerror=()=>{cancelTimeout();if(active && canvas.__buildingPreviewTicket===ticket)onStatus("image-error");};
 img.onload=()=>{
  cancelTimeout();
  if(!active || canvas.__buildingPreviewTicket!==ticket)return;
  if(!img.width || !img.height){onStatus("image-error");return;}
  ctx.clearRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#e9eef2';ctx.fillRect(0,0,canvas.width,canvas.height);
  if(!placement){const scale=Math.min(440/img.width,320/img.height);ctx.drawImage(img,(canvas.width-img.width*scale)/2,(canvas.height-img.height*scale)/2,img.width*scale,img.height*scale);onStatus("ready");return;}
  const TILE_WIDTH=80,TILE_HEIGHT=40,FOOTPRINT_MARGIN=1.04,PADDING=18;
  const cols=placement.width,rows=placement.height,contentWidth=placement.contentWidth;
  if(!Number.isInteger(cols)||!Number.isInteger(rows)||cols<1||rows<1||!Number.isFinite(contentWidth)||contentWidth<=0){onStatus("invalid");return;}
  const project=(c,r)=>({x:(c-r)*TILE_WIDTH/2,y:(c+r)*TILE_HEIGHT/2});
  const front=placement?.tower?project(cols/2,rows/2):project(cols,rows),baseWidth=placement?.tower?img.width*112/207:(cols+rows)*TILE_WIDTH/2*FOOTPRINT_MARGIN/contentWidth,baseHeight=baseWidth*img.height/img.width;
  const imageWidth=baseWidth+Number(widthAdjustment||0),imageHeight=baseHeight+Number(heightAdjustment||0);if(imageWidth<=0||imageHeight<=0){onStatus("invalid");return;}
  const imageLeft=front.x-Number(anchorX)*imageWidth,imageTop=front.y-Number(anchorY)*imageHeight;
  const currentShadowCenter=project(cols/2+Number(currentShadowColumnOffset),rows/2+Number(currentShadowRowOffset));
  const buildShadowOutline=(currentLayerScale)=>{const currentHalfColumn=cols*Number(currentShadowColumnScale)*currentLayerScale/2,currentHalfRow=rows*Number(currentShadowRowScale)*currentLayerScale/2;return (currentShadowShape==='circle'?Array.from({length:48},(_,index)=>({column:Math.cos(index*Math.PI/24)*currentHalfColumn,row:Math.sin(index*Math.PI/24)*currentHalfRow})):[{column:-currentHalfColumn,row:-currentHalfRow},{column:currentHalfColumn,row:-currentHalfRow},{column:currentHalfColumn,row:currentHalfRow},{column:-currentHalfColumn,row:currentHalfRow}]).map(point=>{const offset=project(point.column,point.row);return {x:currentShadowCenter.x+offset.x,y:currentShadowCenter.y+offset.y};});};
  const bounds=[...buildShadowOutline(1),project(-1,-1),project(cols+1,-1),project(-1,rows+1),project(cols+1,rows+1),{x:imageLeft,y:imageTop},{x:imageLeft+imageWidth,y:imageTop+imageHeight}];
  const minX=Math.min(...bounds.map(p=>p.x)),maxX=Math.max(...bounds.map(p=>p.x)),minY=Math.min(...bounds.map(p=>p.y)),maxY=Math.max(...bounds.map(p=>p.y));
  const scale=Math.min((canvas.width-2*PADDING)/(maxX-minX),(canvas.height-2*PADDING)/(maxY-minY));
  ctx.save();ctx.translate((canvas.width-(maxX-minX)*scale)/2-minX*scale,(canvas.height-(maxY-minY)*scale)/2-minY*scale);ctx.scale(scale,scale);
  const outline=(c,r)=>{const points=[project(c,r),project(c+1,r),project(c+1,r+1),project(c,r+1)];ctx.beginPath();ctx.moveTo(points[0].x,points[0].y);for(const p of points.slice(1))ctx.lineTo(p.x,p.y);ctx.closePath();};
  if(options.showTileOverlay!==false)for(let r=-1;r<=rows;r++)for(let c=-1;c<=cols;c++){outline(c,r);ctx.fillStyle=c>=0&&c<cols&&r>=0&&r<rows?'#c2d6a3':'#d8dfd4';ctx.fill();ctx.strokeStyle='#aab8a4';ctx.lineWidth=1/scale;ctx.stroke();}
  for(const layer of [{scale:1,alpha:.14},{scale:.78,alpha:.20},{scale:.5,alpha:.26}]){const points=buildShadowOutline(layer.scale);ctx.beginPath();ctx.moveTo(points[0].x,points[0].y);for(const point of points.slice(1))ctx.lineTo(point.x,point.y);ctx.closePath();ctx.fillStyle=`rgba(24,32,27,${layer.alpha})`;ctx.fill();}
  ctx.drawImage(img,imageLeft,imageTop,imageWidth,imageHeight);
  if(options.showTileOverlay!==false)for(let r=-1;r<=rows;r++)for(let c=-1;c<=cols;c++){const occupied=c>=0&&c<cols&&r>=0&&r<rows;outline(c,r);ctx.strokeStyle=occupied?'#f1b900':'#737d82';ctx.lineWidth=(occupied?1.5:1)/scale;ctx.setLineDash(occupied?[]:[4/scale,4/scale]);ctx.stroke();}
  ctx.setLineDash([]);ctx.strokeStyle='#ef3340';ctx.lineWidth=2/scale;ctx.beginPath();ctx.moveTo(front.x-8/scale,front.y);ctx.lineTo(front.x+8/scale,front.y);ctx.moveTo(front.x,front.y-8/scale);ctx.lineTo(front.x,front.y+8/scale);ctx.stroke();ctx.restore();
  onStatus("ready");
 };
 img.src=preview;
 return ()=>{active=false;cancelTimeout();img.onload=null;img.onerror=null;};
}
