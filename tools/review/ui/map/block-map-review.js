const MIN_MAP_SCALE=0.05,MAX_MAP_SCALE=4,MAP_ZOOM_FACTOR=1.25,MAP_DRAG_THRESHOLD=4;
let activeMapPointer=null,suppressMarkerClick=false;
const currentMapCanvas=document.querySelector('#map'),currentDrawingContext=currentMapCanvas.getContext('2d');
async function fetchMapReviewRecord(currentFilePath){const currentFetchResponse=await fetch(currentFilePath,{cache:'no-store'});if(!currentFetchResponse.ok)throw Error(`맵 데이터 로드 실패: ${currentFilePath}`);return currentFetchResponse.json()}
const availableMapRecords=await fetchMapReviewRecord('block-map-index.json');
const selectedMapIdentifier=new URLSearchParams(location.search).get('map')||availableMapRecords[0].id;
const selectedMapRecord=availableMapRecords.find(currentMapEntry=>currentMapEntry.id===selectedMapIdentifier);
if(!selectedMapRecord){document.querySelector('#status').textContent='등록되지 않은 맵입니다.';throw Error('등록되지 않은 맵: '+selectedMapIdentifier)}
for(const currentMapEntry of availableMapRecords){const currentMapOption=document.createElement('option');currentMapOption.value=currentMapEntry.id;currentMapOption.textContent=currentMapEntry.name;document.querySelector('#map-select').append(currentMapOption)}
document.querySelector('#map-select').value=selectedMapIdentifier;
document.querySelector('#load-map').onclick=()=>{const selectedMapUrl=new URL(location.href);selectedMapUrl.searchParams.set('map',document.querySelector('#map-select').value);location.assign(selectedMapUrl)};
const currentMapRecord=await fetchMapReviewRecord(selectedMapRecord.path);
document.querySelector('#map-title').textContent=currentMapRecord.name+' · 마을 맵 검수';
const currentMaterialColors=await fetch('block-materials.json').then(currentResponse=>currentResponse.json());
const buildingTileRecords=await fetchMapReviewRecord('block-building-tiles.json');
const currentTextureRecords=await fetchMapReviewRecord('block-textures.json');
const loadedTextureImages={};
await Promise.all(Object.entries(currentTextureRecords).map(([currentTextureName,currentTextureRecord])=>new Promise((resolveTextureLoad,rejectTextureLoad)=>{const currentTextureImage=new Image();currentTextureImage.onload=()=>{loadedTextureImages[currentTextureName]=currentTextureImage;resolveTextureLoad()};currentTextureImage.onerror=()=>{document.querySelector('#status').textContent='타일 로드 실패: '+currentTextureName;rejectTextureLoad(Error(currentTextureName))};currentTextureImage.src=currentTextureRecord.path})));
const groundTextureNames={grass:'grass',paving:'paving',water:'spring_water'};
// 각 면의 실제 좌표에서 UV를 계산해 층 경계에서도 벽 타일이 이어지게 한다.
function drawTexturedSurface(currentFaceRecord,currentTextureImage){
 const currentFaceVertices=currentFaceRecord.vertices;
 const currentAlongColumn=Math.max(...currentFaceVertices.map(currentVertexPoint=>currentVertexPoint.column))-Math.min(...currentFaceVertices.map(currentVertexPoint=>currentVertexPoint.column))>0.001;
 // 경사면의 높은 점→낮은 점을 텍스처의 세로 방향으로 삼는다.
 const highestRoofVertex=currentFaceVertices.reduce((currentHighestPoint,currentVertexPoint)=>currentVertexPoint.height>currentHighestPoint.height?currentVertexPoint:currentHighestPoint);
 const lowestRoofVertex=currentFaceVertices.reduce((currentLowestPoint,currentVertexPoint)=>currentVertexPoint.height<currentLowestPoint.height?currentVertexPoint:currentLowestPoint);
 const hasRoofSlope=currentFaceRecord.top&&highestRoofVertex.height-lowestRoofVertex.height>0.001;
 const roofSlopeColumn=currentFaceVertices.some(currentVertexPoint=>Math.abs(currentVertexPoint.row-highestRoofVertex.row)<0.001&&Math.abs(currentVertexPoint.height-highestRoofVertex.height)>0.001);
 const matchingLowVertex=hasRoofSlope?currentFaceVertices.find(currentVertexPoint=>Math.abs((roofSlopeColumn?currentVertexPoint.row:currentVertexPoint.column)-(roofSlopeColumn?highestRoofVertex.row:highestRoofVertex.column))<0.001&&currentVertexPoint.height<highestRoofVertex.height):null;
 const roofDownhillSign=matchingLowVertex?Math.sign(roofSlopeColumn?matchingLowVertex.column-highestRoofVertex.column:matchingLowVertex.row-highestRoofVertex.row):1;
 const currentTexturePoints=currentFaceVertices.map(currentVertexPoint=>{
  if(currentFaceRecord.roofFacingSign)return {x:-currentVertexPoint.row*currentFaceRecord.roofFacingSign*currentTextureImage.width,y:(currentVertexPoint.column-(currentFaceRecord.building.width-1)/2)*currentFaceRecord.roofFacingSign*currentTextureImage.height};
  if(hasRoofSlope)return {x:(roofSlopeColumn?-currentVertexPoint.row:currentVertexPoint.column)*roofDownhillSign*currentTextureImage.width,y:(roofSlopeColumn?currentVertexPoint.column:currentVertexPoint.row)*roofDownhillSign*currentTextureImage.height};
  return {x:(currentFaceRecord.top?currentVertexPoint.column:currentAlongColumn?currentVertexPoint.column+0.5:currentVertexPoint.row+0.5)*currentTextureImage.width,y:(currentFaceRecord.top?currentVertexPoint.row:1-currentVertexPoint.height/48)*currentTextureImage.height};
 });
 for(let currentTriangleIndex=1;currentTriangleIndex<currentFaceVertices.length-1;currentTriangleIndex++){
  const currentTriangleIndices=[0,currentTriangleIndex,currentTriangleIndex+1];
  const [texturePointFirst,texturePointSecond,texturePointThird]=currentTriangleIndices.map(currentVertexIndex=>currentTexturePoints[currentVertexIndex]);
  const [screenPointFirst,screenPointSecond,screenPointThird]=currentTriangleIndices.map(currentVertexIndex=>currentFaceRecord.points[currentVertexIndex]);
  const textureDeltaFirstX=texturePointSecond.x-texturePointFirst.x,textureDeltaFirstY=texturePointSecond.y-texturePointFirst.y,textureDeltaSecondX=texturePointThird.x-texturePointFirst.x,textureDeltaSecondY=texturePointThird.y-texturePointFirst.y;
  const currentDeterminantValue=textureDeltaFirstX*textureDeltaSecondY-textureDeltaSecondX*textureDeltaFirstY;
  if(Math.abs(currentDeterminantValue)<0.001)continue;
  const screenDeltaFirstX=screenPointSecond.x-screenPointFirst.x,screenDeltaFirstY=screenPointSecond.y-screenPointFirst.y,screenDeltaSecondX=screenPointThird.x-screenPointFirst.x,screenDeltaSecondY=screenPointThird.y-screenPointFirst.y;
  const affineScaleFirst=(screenDeltaFirstX*textureDeltaSecondY-screenDeltaSecondX*textureDeltaFirstY)/currentDeterminantValue,affineSkewFirst=(screenDeltaFirstY*textureDeltaSecondY-screenDeltaSecondY*textureDeltaFirstY)/currentDeterminantValue,affineSkewSecond=(screenDeltaSecondX*textureDeltaFirstX-screenDeltaFirstX*textureDeltaSecondX)/currentDeterminantValue,affineScaleSecond=(screenDeltaSecondY*textureDeltaFirstX-screenDeltaFirstY*textureDeltaSecondX)/currentDeterminantValue;
  currentDrawingContext.save();currentDrawingContext.beginPath();currentDrawingContext.moveTo(screenPointFirst.x,screenPointFirst.y);currentDrawingContext.lineTo(screenPointSecond.x,screenPointSecond.y);currentDrawingContext.lineTo(screenPointThird.x,screenPointThird.y);currentDrawingContext.closePath();currentDrawingContext.clip();
  currentDrawingContext.transform(affineScaleFirst,affineSkewFirst,affineSkewSecond,affineScaleSecond,screenPointFirst.x-affineScaleFirst*texturePointFirst.x-affineSkewSecond*texturePointFirst.y,screenPointFirst.y-affineSkewFirst*texturePointFirst.x-affineScaleSecond*texturePointFirst.y);
  currentDrawingContext.fillStyle=currentDrawingContext.createPattern(currentTextureImage,'repeat');const currentTextureMinX=Math.min(...currentTexturePoints.map(currentPointValue=>currentPointValue.x)),currentTextureMinY=Math.min(...currentTexturePoints.map(currentPointValue=>currentPointValue.y));currentDrawingContext.fillRect(currentTextureMinX,currentTextureMinY,Math.max(...currentTexturePoints.map(currentPointValue=>currentPointValue.x))-currentTextureMinX,Math.max(...currentTexturePoints.map(currentPointValue=>currentPointValue.y))-currentTextureMinY);currentDrawingContext.restore();
 }
}
let currentCameraRotation=0,currentScaleValue=1,currentOffsetX=0,currentOffsetY=0,currentCharacterCell=currentMapRecord.startPoint;
const currentBlockedCells=new Set(currentMapRecord.blocked.map(currentCell=>`${currentCell.column},${currentCell.row}`));
function projectBlockVertex(currentVertexPoint){let currentColumnValue=currentVertexPoint.column,currentRowValue=currentVertexPoint.row;for(let currentRotationIndex=0;currentRotationIndex<currentCameraRotation;currentRotationIndex++)[currentColumnValue,currentRowValue]=[-currentRowValue,currentColumnValue];return {x:(currentColumnValue-currentRowValue)*80,y:(currentColumnValue+currentRowValue)*40-(currentVertexPoint.height??0)}}
function drawSurfacePolygon(currentSurfacePoints,currentFillColor){currentDrawingContext.beginPath();currentSurfacePoints.forEach((currentPointValue,currentPointIndex)=>currentPointIndex?currentDrawingContext.lineTo(currentPointValue.x,currentPointValue.y):currentDrawingContext.moveTo(currentPointValue.x,currentPointValue.y));currentDrawingContext.closePath();currentDrawingContext.fillStyle=currentFillColor;currentDrawingContext.fill();if(document.querySelector('#edges').checked){currentDrawingContext.strokeStyle='#354039';currentDrawingContext.lineWidth=1/currentScaleValue;currentDrawingContext.stroke()}}
// 층 경계를 넘는 블록 면은 48px 층 단위로 분리한다.
// 홀수 폭의 평평한 용마루도 중앙에서 나눠 양쪽 처마 방향을 적용한다.
function splitRoofDirections(currentFaceRecord,currentBuildingRecord){
 if(!currentFaceRecord.top||currentFaceRecord.material!=='roof')return [currentFaceRecord];
 const roofCenterColumn=(currentBuildingRecord.width-1)/2;
 return [-1,1].map(currentFacingSign=>{
  const clippedRoofVertices=[];
  currentFaceRecord.vertices.forEach((currentVertexPoint,currentVertexIndex)=>{
   const nextVertexPoint=currentFaceRecord.vertices[(currentVertexIndex+1)%currentFaceRecord.vertices.length];
   const currentInsideHalf=(currentVertexPoint.column-roofCenterColumn)*currentFacingSign>=0,nextInsideHalf=(nextVertexPoint.column-roofCenterColumn)*currentFacingSign>=0;
   if(currentInsideHalf)clippedRoofVertices.push(currentVertexPoint);
   if(currentInsideHalf!==nextInsideHalf){const currentEdgeFraction=(roofCenterColumn-currentVertexPoint.column)/(nextVertexPoint.column-currentVertexPoint.column);clippedRoofVertices.push({column:roofCenterColumn,row:currentVertexPoint.row+(nextVertexPoint.row-currentVertexPoint.row)*currentEdgeFraction,height:currentVertexPoint.height+(nextVertexPoint.height-currentVertexPoint.height)*currentEdgeFraction})}
  });
  return {...currentFaceRecord,vertices:clippedRoofVertices,roofFacingSign:currentFacingSign};
 }).filter(currentSplitFace=>currentSplitFace.vertices.length>=3);
}
function splitWallFloors(currentFaceRecord){
 if(currentFaceRecord.top)return [currentFaceRecord];
 const minimumFaceHeight=Math.min(...currentFaceRecord.vertices.map(currentVertexPoint=>currentVertexPoint.height)),maximumFaceHeight=Math.max(...currentFaceRecord.vertices.map(currentVertexPoint=>currentVertexPoint.height));
 const splitFaceRecords=[];
 for(let currentFloorIndex=Math.floor(minimumFaceHeight/48);currentFloorIndex<Math.ceil(maximumFaceHeight/48);currentFloorIndex++){
  let clippedFaceVertices=currentFaceRecord.vertices;
  for(const [currentClipHeight,currentKeepAbove] of [[currentFloorIndex*48,true],[(currentFloorIndex+1)*48,false]]){
   const previousFaceVertices=clippedFaceVertices;clippedFaceVertices=[];
   previousFaceVertices.forEach((currentVertexPoint,currentVertexIndex)=>{const nextVertexPoint=previousFaceVertices[(currentVertexIndex+1)%previousFaceVertices.length];const currentInsidePlane=currentKeepAbove?currentVertexPoint.height>=currentClipHeight:currentVertexPoint.height<=currentClipHeight,nextInsidePlane=currentKeepAbove?nextVertexPoint.height>=currentClipHeight:nextVertexPoint.height<=currentClipHeight;if(currentInsidePlane)clippedFaceVertices.push(currentVertexPoint);if(currentInsidePlane!==nextInsidePlane){const currentEdgeFraction=(currentClipHeight-currentVertexPoint.height)/(nextVertexPoint.height-currentVertexPoint.height);clippedFaceVertices.push({column:currentVertexPoint.column+(nextVertexPoint.column-currentVertexPoint.column)*currentEdgeFraction,row:currentVertexPoint.row+(nextVertexPoint.row-currentVertexPoint.row)*currentEdgeFraction,height:currentClipHeight})}});
  }
  if(clippedFaceVertices.length>=3)splitFaceRecords.push({...currentFaceRecord,vertices:clippedFaceVertices,floorIndex:currentFloorIndex});
 }
 return splitFaceRecords;
}
function selectWallTexture(currentFaceRecord){
 if(currentFaceRecord.top)return 'roof';
 const currentBuildingRecord=currentFaceRecord.building;
 const currentColumnMinimum=Math.min(...currentFaceRecord.vertices.map(currentVertexPoint=>currentVertexPoint.column)),currentColumnMaximum=Math.max(...currentFaceRecord.vertices.map(currentVertexPoint=>currentVertexPoint.column)),currentRowMinimum=Math.min(...currentFaceRecord.vertices.map(currentVertexPoint=>currentVertexPoint.row)),currentRowMaximum=Math.max(...currentFaceRecord.vertices.map(currentVertexPoint=>currentVertexPoint.row));
 const wallAlongColumn=currentColumnMaximum-currentColumnMinimum>0.001;
 const currentWallIndex=Math.floor((wallAlongColumn?currentColumnMinimum:currentRowMinimum)+0.5);
 const entranceColumnLocal=currentBuildingRecord.entrance.column-currentBuildingRecord.origin.column,entranceRowLocal=currentBuildingRecord.entrance.row-currentBuildingRecord.origin.row;
 const isEntranceFace=wallAlongColumn?Math.abs(entranceColumnLocal-(currentColumnMinimum+currentColumnMaximum)/2)<0.01&&Math.abs(entranceRowLocal-currentRowMinimum- Math.sign(entranceRowLocal-currentRowMinimum)*0.5)<0.01:Math.abs(entranceRowLocal-(currentRowMinimum+currentRowMaximum)/2)<0.01&&Math.abs(entranceColumnLocal-currentColumnMinimum-Math.sign(entranceColumnLocal-currentColumnMinimum)*0.5)<0.01;
 if(currentFaceRecord.floorIndex===0&&isEntranceFace)return 'door';
 // 처마보다 높은 박공 벽에는 창문을 배치하지 않는다.
 const roofBaseHeight=Math.min(...currentBuildingRecord.blocks.filter(currentBlockRecord=>currentBlockRecord.material==='roof').map(currentBlockRecord=>currentBlockRecord.layer*32+(currentBlockRecord.offsetHeight||0)));
 if(Math.min(...currentFaceRecord.vertices.map(currentVertexPoint=>currentVertexPoint.height))>=roofBaseHeight)return 'wall';
 if(currentFaceRecord.floorIndex===0)return currentWallIndex%2===0?'window':'wall';
 return currentWallIndex%2===0?'window':'large_window';
}
function renderBlockMap(currentFitRequested=false){currentMapCanvas.width=currentMapCanvas.clientWidth;currentMapCanvas.height=currentMapCanvas.clientHeight;const currentAllCorners=[{column:0,row:0},{column:currentMapRecord.columns,row:0},{column:0,row:currentMapRecord.rows},{column:currentMapRecord.columns,row:currentMapRecord.rows}].map(projectBlockVertex);if(currentFitRequested){const currentMinX=Math.min(...currentAllCorners.map(p=>p.x)),currentMaxX=Math.max(...currentAllCorners.map(p=>p.x)),currentMinY=Math.min(...currentAllCorners.map(p=>p.y))-120,currentMaxY=Math.max(...currentAllCorners.map(p=>p.y))+40;currentScaleValue=Math.min(currentMapCanvas.width/(currentMaxX-currentMinX+160),currentMapCanvas.height/(currentMaxY-currentMinY+80));currentOffsetX=currentMapCanvas.width/2-(currentMinX+currentMaxX)/2*currentScaleValue;currentOffsetY=currentMapCanvas.height/2-(currentMinY+currentMaxY)/2*currentScaleValue}
document.querySelector('#zoom-level').textContent=Math.round(currentScaleValue*100)+'%';
document.querySelector('#zoom-in').disabled=currentScaleValue>=MAX_MAP_SCALE;document.querySelector('#zoom-out').disabled=currentScaleValue<=MIN_MAP_SCALE;
currentDrawingContext.setTransform(currentScaleValue,0,0,currentScaleValue,currentOffsetX,currentOffsetY);
for(let currentRowIndex=0;currentRowIndex<currentMapRecord.rows;currentRowIndex++)for(let currentColumnIndex=0;currentColumnIndex<currentMapRecord.columns;currentColumnIndex++){const currentTerrainName=currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentRowIndex][currentColumnIndex]];drawSurfacePolygon([[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]].map(([c,r])=>projectBlockVertex({column:currentColumnIndex+c,row:currentRowIndex+r})),currentMaterialColors[currentTerrainName]);const currentGroundImage=loadedTextureImages[groundTextureNames[currentTerrainName]];if(currentGroundImage){const currentGroundVertices=[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]].map(([currentColumnOffset,currentRowOffset])=>({column:currentColumnIndex+currentColumnOffset,row:currentRowIndex+currentRowOffset,height:0}));drawTexturedSurface({top:true,vertices:currentGroundVertices,points:currentGroundVertices.map(projectBlockVertex)},currentGroundImage)}}
const currentRenderFaces=currentMapRecord.buildings.flatMap(currentBuilding=>currentBuilding.faces.flatMap(currentFaceRecord=>splitRoofDirections(currentFaceRecord,currentBuilding)).flatMap(splitWallFloors).map(currentFace=>({...currentFace,building:currentBuilding,textureTiles:buildingTileRecords[currentBuilding.id]||buildingTileRecords['iseulon-'+currentBuilding.facilityKind],points:currentFace.vertices.map(currentVertex=>projectBlockVertex({column:currentBuilding.origin.column+currentVertex.column,row:currentBuilding.origin.row+currentVertex.row,height:currentVertex.height})),depth:currentFace.vertices.reduce((s,v)=>s+projectBlockVertex({column:currentBuilding.origin.column+v.column,row:currentBuilding.origin.row+v.row}).y,0)/currentFace.vertices.length}))).sort((a,b)=>a.depth-b.depth);
for(const currentFace of currentRenderFaces){const currentAreaValue=currentFace.points.reduce((s,p,i)=>{const n=currentFace.points[(i+1)%currentFace.points.length];return s+p.x*n.y-n.x*p.y},0);if(currentFace.top||currentAreaValue>0){drawSurfacePolygon(currentFace.points,currentMaterialColors[currentFace.material]);// 지붕 경사 측면은 막힌 벽으로 두고 일반 벽 구간에만 창문을 교차 배치한다.
const currentTextureRole=selectWallTexture(currentFace);
const currentTextureName=currentFace.textureTiles[currentTextureRole];drawTexturedSurface(currentFace,loadedTextureImages[currentTextureName])}}
const currentMarkerPoint=projectBlockVertex(currentCharacterCell);currentDrawingContext.fillStyle='#f5d680';currentDrawingContext.fillRect(currentMarkerPoint.x-8,currentMarkerPoint.y-80,16,80);currentDrawingContext.setTransform(1,0,0,1,0,0);document.querySelector('#status').textContent=`회전 ${currentCameraRotation*90}° · 건물 ${currentMapRecord.buildings.length}개 · 블록 ${currentMapRecord.buildings.reduce((s,b)=>s+b.blocks.length,0)}개 · 검수 마커 높이 80 · 지붕 보행 불가`}
currentMapRecord.buildings.forEach(currentBuilding=>{const currentOption=document.createElement('option');currentOption.value=currentBuilding.id;currentOption.textContent=currentBuilding.name;document.querySelector('#building').append(currentOption)});
document.querySelector('#building').onchange=currentEvent=>{const currentBuilding=currentMapRecord.buildings.find(b=>b.id===currentEvent.target.value);if(!currentBuilding)return;const currentCenter=projectBlockVertex({column:currentBuilding.origin.column+currentBuilding.width/2-.5,row:currentBuilding.origin.row+currentBuilding.height/2-.5,height:48});currentScaleValue=1;currentOffsetX=currentMapCanvas.width/2-currentCenter.x;currentOffsetY=currentMapCanvas.height/2-currentCenter.y;renderBlockMap()};
document.querySelector('#rotate').onclick=()=>{currentCameraRotation=(currentCameraRotation+1)%4;renderBlockMap(true)};document.querySelector('#fit').onclick=()=>renderBlockMap(true);document.querySelector('#edges').onchange=()=>renderBlockMap();window.onresize=()=>renderBlockMap(true);
currentMapCanvas.onclick=currentEvent=>{if(suppressMarkerClick){suppressMarkerClick=false;return;}const currentBounds=currentMapCanvas.getBoundingClientRect(),currentWorldX=(currentEvent.clientX-currentBounds.left-currentOffsetX)/currentScaleValue,currentWorldY=(currentEvent.clientY-currentBounds.top-currentOffsetY)/currentScaleValue;let currentColumnValue=(currentWorldX/80+currentWorldY/40)/2,currentRowValue=(currentWorldY/40-currentWorldX/80)/2;for(let i=0;i<currentCameraRotation;i++)[currentColumnValue,currentRowValue]=[currentRowValue,-currentColumnValue];currentColumnValue=Math.round(currentColumnValue);currentRowValue=Math.round(currentRowValue);if(currentColumnValue<0||currentColumnValue>=currentMapRecord.columns||currentRowValue<0||currentRowValue>=currentMapRecord.rows||currentBlockedCells.has(`${currentColumnValue},${currentRowValue}`))return;currentCharacterCell={column:currentColumnValue,row:currentRowValue};renderBlockMap()};renderBlockMap(true);

// 포인터 아래의 지형 좌표를 유지하면서 배율을 변경한다.
function changeMapZoom(currentZoomFactor,currentAnchorX=currentMapCanvas.width/2,currentAnchorY=currentMapCanvas.height/2){
 const nextScaleValue=Math.max(MIN_MAP_SCALE,Math.min(MAX_MAP_SCALE,currentScaleValue*currentZoomFactor));
 currentOffsetX=currentAnchorX-(currentAnchorX-currentOffsetX)*nextScaleValue/currentScaleValue;
 currentOffsetY=currentAnchorY-(currentAnchorY-currentOffsetY)*nextScaleValue/currentScaleValue;
 currentScaleValue=nextScaleValue;renderBlockMap();
}
document.querySelector('#zoom-in').onclick=()=>changeMapZoom(MAP_ZOOM_FACTOR);
document.querySelector('#zoom-out').onclick=()=>changeMapZoom(1/MAP_ZOOM_FACTOR);
currentMapCanvas.addEventListener('wheel',currentPointerEvent=>{currentPointerEvent.preventDefault();const currentCanvasBounds=currentMapCanvas.getBoundingClientRect();changeMapZoom(Math.exp(-Math.max(-100,Math.min(100,currentPointerEvent.deltaY))*0.002),currentPointerEvent.clientX-currentCanvasBounds.left,currentPointerEvent.clientY-currentCanvasBounds.top)},{passive:false});
currentMapCanvas.onpointerdown=currentPointerEvent=>{if(currentPointerEvent.button!==0)return;suppressMarkerClick=false;activeMapPointer={id:currentPointerEvent.pointerId,x:currentPointerEvent.clientX,y:currentPointerEvent.clientY,offsetX:currentOffsetX,offsetY:currentOffsetY};currentMapCanvas.setPointerCapture(currentPointerEvent.pointerId)};
currentMapCanvas.onpointermove=currentPointerEvent=>{if(!activeMapPointer||activeMapPointer.id!==currentPointerEvent.pointerId)return;const currentDeltaX=currentPointerEvent.clientX-activeMapPointer.x,currentDeltaY=currentPointerEvent.clientY-activeMapPointer.y;if(!suppressMarkerClick&&Math.hypot(currentDeltaX,currentDeltaY)<MAP_DRAG_THRESHOLD)return;suppressMarkerClick=true;currentMapCanvas.style.cursor='grabbing';currentOffsetX=activeMapPointer.offsetX+currentDeltaX;currentOffsetY=activeMapPointer.offsetY+currentDeltaY;renderBlockMap()};
function finishMapDrag(){activeMapPointer=null;currentMapCanvas.style.cursor='grab'}
currentMapCanvas.onpointerup=finishMapDrag;currentMapCanvas.onpointercancel=finishMapDrag;currentMapCanvas.onlostpointercapture=finishMapDrag;
