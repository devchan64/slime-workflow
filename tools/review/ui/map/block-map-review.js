const MIN_MAP_SCALE=0.05,MAX_MAP_SCALE=4,MAP_ZOOM_FACTOR=1.25,MAP_DRAG_THRESHOLD=4,MAP_KEYBOARD_PAN_DISTANCE=48;
let activeMapPointer=null,suppressMarkerClick=false;
const currentMapCanvas=document.querySelector('#map'),currentDrawingContext=currentMapCanvas.getContext('2d');
async function fetchMapReviewRecord(currentFilePath){const currentFetchResponse=await fetch(currentFilePath,{cache:'no-store'});if(!currentFetchResponse.ok)throw Error(`맵 데이터 로드 실패: ${currentFilePath}`);return currentFetchResponse.json()}
const gameRenderMetrics=await fetchMapReviewRecord('game-render-metrics.json');
const blockRenderProfile=await fetchMapReviewRecord('block-render-profile.json');
const TOWN_BLOCK_HEIGHT=blockRenderProfile.blockHeight;
const BLOCK_BOUNDARY_COLOR='#dce5ef';
if(!Number.isInteger(TOWN_BLOCK_HEIGHT)||TOWN_BLOCK_HEIGHT<=0)throw Error('마을 블록 높이 설정이 올바르지 않습니다.');
const townHalfTileWidth=gameRenderMetrics.townTileWidth/2,townHalfTileHeight=gameRenderMetrics.townTileHeight/2;
const availableMapRecords=await fetchMapReviewRecord('block-map-index.json');
const selectedMapIdentifier=new URLSearchParams(location.search).get('map')||availableMapRecords[0].id;
const isTownSpecificReviewPage=new URLSearchParams(location.search).get('townPage')==='1';
const selectedMapRecord=availableMapRecords.find(currentMapEntry=>currentMapEntry.id===selectedMapIdentifier);
if(!selectedMapRecord){document.querySelector('#status').textContent='등록되지 않은 맵입니다.';throw Error('등록되지 않은 맵: '+selectedMapIdentifier)}
for(const currentMapEntry of availableMapRecords){const currentMapOption=document.createElement('option');currentMapOption.value=currentMapEntry.id;currentMapOption.textContent=currentMapEntry.name;document.querySelector('#map-select').append(currentMapOption)}
document.querySelector('#map-select').value=selectedMapIdentifier;
if(isTownSpecificReviewPage){document.querySelector('#map-select').closest('label').hidden=true;document.querySelector('#load-map').hidden=true}
document.querySelector('#load-map').onclick=()=>{const selectedMapUrl=new URL(location.href);selectedMapUrl.searchParams.set('map',document.querySelector('#map-select').value);location.assign(selectedMapUrl)};
const currentMapRecord=await fetchMapReviewRecord(selectedMapRecord.path);
const currentReviewTitle=currentMapRecord.name+' · '+currentMapRecord.reviewLabel;
document.querySelector('#map-title').textContent=currentReviewTitle;
document.title=currentReviewTitle;
document.querySelector('.map-toolbar').setAttribute('aria-label',currentMapRecord.reviewLabel+' 도구');
currentMapCanvas.setAttribute('aria-label',currentReviewTitle+'. 방향키로 이동하고 더하기와 빼기 키로 확대 또는 축소하며 0 키로 전체 보기를 적용합니다.');
const currentMaterialColors=await fetch('block-materials.json').then(currentResponse=>currentResponse.json());
const buildingTileRecords=await fetchMapReviewRecord('block-building-tiles.json');
const currentTextureRecords=await fetchMapReviewRecord('/management/map-assets/textures');
const loadedTextureImages={};
await Promise.all(Object.entries(currentTextureRecords).map(([currentTextureName,currentTextureRecord])=>new Promise((resolveTextureLoad,rejectTextureLoad)=>{const currentTextureImage=new Image();currentTextureImage.onload=()=>{loadedTextureImages[currentTextureName]=currentTextureImage;resolveTextureLoad()};currentTextureImage.onerror=()=>{document.querySelector('#status').textContent='타일 로드 실패: '+currentTextureName;rejectTextureLoad(Error(currentTextureName))};currentTextureImage.src=new URL(currentTextureRecord.path,import.meta.url).href})));
const reviewCharacterRecord=await fetchMapReviewRecord('review-character.json');
const reviewCharacterImage=new Image();
await new Promise((resolveCharacterLoad,rejectCharacterLoad)=>{reviewCharacterImage.onload=resolveCharacterLoad;reviewCharacterImage.onerror=()=>rejectCharacterLoad(Error('기본 캐릭터 로드 실패'));reviewCharacterImage.src=new URL(reviewCharacterRecord.image,import.meta.url).href});
const groundTextureNames={grass:currentMapRecord.id==='iseulon'?'iseulon-grass-mud-frame':'grass',paving:currentMapRecord.id==='stonewarm'?'stonewarm-marble-paving':currentMapRecord.id==='saltford'?'stonewarm-gravel-paving':['reedhaven','grainstead'].includes(currentMapRecord.id)?'reedhaven-dirt-road':'paving',gravel:currentMapRecord.id==='stonewarm'?'stonewarm-exposed-rock-ground':'gravel',flowers:'flower_bed',dew:'dew',ash:'ash',moss:'moss','leaf-litter':'leaf-litter','tree-base':'tree-base',wall:'cliff-wall',stone:'stone','dry-soil-branches':'dry-soil-branches',mud:'mud',boulder:'boulder',cactus:'cactus',road:'packed_dirt_road',water:'spring_water','deep-water':'deep-water','shallow-water':'shallow-water','reed-bed':'reed-bed'};
function readBuildingTileSet(currentBuildingRecord){return {...buildingTileRecords['iseulon-'+currentBuildingRecord.facilityKind],...(currentMapRecord.buildingTileOverrides||{}),...(buildingTileRecords[currentBuildingRecord.id]||{})}}
function renderAppliedTileSourceList(){
 const appliedTextureNames=new Set();
 Object.values(currentMapRecord.terrainCodes).forEach(currentTerrainName=>{const currentTextureName=groundTextureNames[currentTerrainName];if(currentTextureName)appliedTextureNames.add(currentTextureName)});
 currentMapRecord.buildings.forEach(currentBuildingRecord=>Object.values(readBuildingTileSet(currentBuildingRecord)).forEach(currentTextureName=>appliedTextureNames.add(currentTextureName)));
 const appliedTileList=document.querySelector('#applied-tile-list');appliedTileList.replaceChildren();
 [...appliedTextureNames].sort().forEach(currentTextureName=>{
  const currentTextureRecord=currentTextureRecords[currentTextureName];const currentListItem=document.createElement('li');const currentName=document.createElement('strong');currentName.textContent=currentTextureName;currentListItem.append(currentName);
  if(!currentTextureRecord){const currentWarning=document.createElement('span');currentWarning.className='tile-source-warning';currentWarning.textContent='⚠ 원본 미등록';currentWarning.title='타일 카탈로그에 원본 파일이 등록되지 않았습니다.';currentListItem.append(currentWarning);appliedTileList.append(currentListItem);return}
  const currentThumbnail=document.createElement('img');currentThumbnail.src=new URL(currentTextureRecord.path,import.meta.url).href;currentThumbnail.alt=`${currentTextureName} 원본 썸네일`;currentThumbnail.loading='lazy';currentListItem.prepend(currentThumbnail);
  const sourceSize=currentTextureRecord.source_size;const expectedSourceSize=currentTextureRecord.expected_source_size;const currentSource=document.createElement('span');currentSource.textContent=`${sourceSize?.join('×')||'?'}px`;currentListItem.append(currentSource);
  const normalizationWarning=currentTextureRecord.normalization_warning||(sourceSize&&expectedSourceSize&&sourceSize.every((currentValue,currentIndex)=>currentValue===expectedSourceSize[currentIndex])?null:`정규화 확인 필요: 기준 ${expectedSourceSize?.join('×')||'256×256'}px`);
  if(normalizationWarning){const currentWarning=document.createElement('span');currentWarning.className='tile-source-warning';currentWarning.textContent='⚠';currentWarning.title=normalizationWarning;const currentDescription=document.createElement('span');currentDescription.className='tile-source-warning-description';currentDescription.textContent=normalizationWarning;currentListItem.append(currentWarning,currentDescription)}
  appliedTileList.append(currentListItem);
 });
}
renderAppliedTileSourceList();
// 각 면의 실제 좌표에서 UV를 계산해 층 경계에서도 벽 타일이 이어지게 한다.
function drawTexturedSurface(currentFaceRecord,currentTextureImage){
 const currentFaceVertices=currentFaceRecord.vertices;
 const currentAlongColumn=Math.max(...currentFaceVertices.map(currentVertexPoint=>currentVertexPoint.column))-Math.min(...currentFaceVertices.map(currentVertexPoint=>currentVertexPoint.column))>0.001;
 const isRoofTileSurface=currentFaceRecord.top&&currentFaceRecord.material==='roof';
 const roofTileMinimumColumn=Math.min(...currentFaceVertices.map(currentVertexPoint=>currentVertexPoint.column));
 const roofTileMaximumRow=Math.max(...currentFaceVertices.map(currentVertexPoint=>currentVertexPoint.row));
 // 경사면의 높은 점→낮은 점을 텍스처의 세로 방향으로 삼는다.
 const highestRoofVertex=currentFaceVertices.reduce((currentHighestPoint,currentVertexPoint)=>currentVertexPoint.height>currentHighestPoint.height?currentVertexPoint:currentHighestPoint);
 const lowestRoofVertex=currentFaceVertices.reduce((currentLowestPoint,currentVertexPoint)=>currentVertexPoint.height<currentLowestPoint.height?currentVertexPoint:currentLowestPoint);
 const hasRoofSlope=currentFaceRecord.top&&highestRoofVertex.height-lowestRoofVertex.height>0.001;
 const roofSlopeColumn=currentFaceVertices.some(currentVertexPoint=>Math.abs(currentVertexPoint.row-highestRoofVertex.row)<0.001&&Math.abs(currentVertexPoint.height-highestRoofVertex.height)>0.001);
 const matchingLowVertex=hasRoofSlope?currentFaceVertices.find(currentVertexPoint=>Math.abs((roofSlopeColumn?currentVertexPoint.row:currentVertexPoint.column)-(roofSlopeColumn?highestRoofVertex.row:highestRoofVertex.column))<0.001&&currentVertexPoint.height<highestRoofVertex.height):null;
 const roofDownhillSign=matchingLowVertex?Math.sign(roofSlopeColumn?matchingLowVertex.column-highestRoofVertex.column:matchingLowVertex.row-highestRoofVertex.row):1;
 const currentTexturePoints=currentFaceVertices.map(currentVertexPoint=>{
  // 지붕 원본의 프레임은 블록 한 칸 전체에만 적용하고, 검수 시점에는 반시계 방향으로 90° 회전한다.
  if(isRoofTileSurface)return {x:(roofTileMaximumRow-currentVertexPoint.row)*currentTextureImage.width,y:(currentVertexPoint.column-roofTileMinimumColumn)*currentTextureImage.height};
  if(hasRoofSlope)return {x:(roofSlopeColumn?-currentVertexPoint.row:currentVertexPoint.column)*roofDownhillSign*currentTextureImage.width,y:(roofSlopeColumn?currentVertexPoint.column:currentVertexPoint.row)*roofDownhillSign*currentTextureImage.height};
  // 바닥은 셀 모서리에서 원본 텍스처가 시작해야 반복 경계가 셀 중앙을 가르지 않는다.
  const groundTextureOffset=currentFaceRecord.ground?0.5:0;
  return {x:(currentFaceRecord.top?currentVertexPoint.column+groundTextureOffset:currentAlongColumn?currentVertexPoint.column+0.5:currentVertexPoint.row+0.5)*currentTextureImage.width,y:(currentFaceRecord.top?currentVertexPoint.row+groundTextureOffset:1-currentVertexPoint.height/TOWN_BLOCK_HEIGHT)*currentTextureImage.height};
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
function projectBlockVertex(currentVertexPoint){let currentColumnValue=currentVertexPoint.column,currentRowValue=currentVertexPoint.row;for(let currentRotationIndex=0;currentRotationIndex<currentCameraRotation;currentRotationIndex++)[currentColumnValue,currentRowValue]=[-currentRowValue,currentColumnValue];return {x:(currentColumnValue-currentRowValue)*townHalfTileWidth,y:(currentColumnValue+currentRowValue)*townHalfTileHeight-(currentVertexPoint.height??0)}}
function drawSurfacePolygon(currentSurfacePoints,currentFillColor){currentDrawingContext.beginPath();currentSurfacePoints.forEach((currentPointValue,currentPointIndex)=>currentPointIndex?currentDrawingContext.lineTo(currentPointValue.x,currentPointValue.y):currentDrawingContext.moveTo(currentPointValue.x,currentPointValue.y));currentDrawingContext.closePath();currentDrawingContext.fillStyle=currentFillColor;currentDrawingContext.fill();if(document.querySelector('#edges').checked){currentDrawingContext.strokeStyle=BLOCK_BOUNDARY_COLOR;currentDrawingContext.lineWidth=1/currentScaleValue;currentDrawingContext.stroke()}}
// 층 경계를 넘는 블록 면은 공용 블록 높이 단위로 분리한다.
function splitWallFloors(currentFaceRecord){
 if(currentFaceRecord.top)return [currentFaceRecord];
 const minimumFaceHeight=Math.min(...currentFaceRecord.vertices.map(currentVertexPoint=>currentVertexPoint.height)),maximumFaceHeight=Math.max(...currentFaceRecord.vertices.map(currentVertexPoint=>currentVertexPoint.height));
 const splitFaceRecords=[];
 for(let currentFloorIndex=Math.floor(minimumFaceHeight/TOWN_BLOCK_HEIGHT);currentFloorIndex<Math.ceil(maximumFaceHeight/TOWN_BLOCK_HEIGHT);currentFloorIndex++){
  let clippedFaceVertices=currentFaceRecord.vertices;
  for(const [currentClipHeight,currentKeepAbove] of [[currentFloorIndex*TOWN_BLOCK_HEIGHT,true],[(currentFloorIndex+1)*TOWN_BLOCK_HEIGHT,false]]){
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
 const roofBaseHeight=Math.min(...currentBuildingRecord.blocks.filter(currentBlockRecord=>currentBlockRecord.material==='roof').map(currentBlockRecord=>currentBlockRecord.layer*TOWN_BLOCK_HEIGHT+(currentBlockRecord.offsetHeight||0)));
 if(Math.min(...currentFaceRecord.vertices.map(currentVertexPoint=>currentVertexPoint.height))>=roofBaseHeight)return 'roof_underlay';
 const wallEntranceDistance=Math.abs(currentWallIndex-Math.round(wallAlongColumn?entranceColumnLocal:entranceRowLocal));
 if(currentFaceRecord.textureTiles.wall==='wood_wall')return wallEntranceDistance%2===0?'wall':'window';
 if(currentFaceRecord.floorIndex===0)return currentWallIndex%2===0?'window':'wall';
 return currentWallIndex%2===0?'window':'large_window';
}
function renderBlockMap(currentFitRequested=false){currentMapCanvas.width=currentMapCanvas.clientWidth;currentMapCanvas.height=currentMapCanvas.clientHeight;const currentAllCorners=[{column:0,row:0},{column:currentMapRecord.columns,row:0},{column:0,row:currentMapRecord.rows},{column:currentMapRecord.columns,row:currentMapRecord.rows}].map(projectBlockVertex);if(currentFitRequested){const currentMinX=Math.min(...currentAllCorners.map(p=>p.x)),currentMaxX=Math.max(...currentAllCorners.map(p=>p.x)),currentMinY=Math.min(...currentAllCorners.map(p=>p.y))-TOWN_BLOCK_HEIGHT*2,currentMaxY=Math.max(...currentAllCorners.map(p=>p.y))+40;currentScaleValue=Math.min(currentMapCanvas.width/(currentMaxX-currentMinX+160),currentMapCanvas.height/(currentMaxY-currentMinY+80));currentOffsetX=currentMapCanvas.width/2-(currentMinX+currentMaxX)/2*currentScaleValue;currentOffsetY=currentMapCanvas.height/2-(currentMinY+currentMaxY)/2*currentScaleValue}
document.querySelector('#zoom-level').textContent=Math.round(currentScaleValue*100)+'%';
document.querySelector('#zoom-in').disabled=currentScaleValue>=MAX_MAP_SCALE;document.querySelector('#zoom-out').disabled=currentScaleValue<=MIN_MAP_SCALE;
currentDrawingContext.setTransform(currentScaleValue,0,0,currentScaleValue,currentOffsetX,currentOffsetY);
for(let currentRowIndex=0;currentRowIndex<currentMapRecord.rows;currentRowIndex++)for(let currentColumnIndex=0;currentColumnIndex<currentMapRecord.columns;currentColumnIndex++){const currentTerrainName=currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentRowIndex][currentColumnIndex]];drawSurfacePolygon([[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]].map(([c,r])=>projectBlockVertex({column:currentColumnIndex+c,row:currentRowIndex+r})),currentMaterialColors[currentTerrainName]);const currentGroundImage=loadedTextureImages[groundTextureNames[currentTerrainName]];if(currentGroundImage){const currentGroundVertices=[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]].map(([currentColumnOffset,currentRowOffset])=>({column:currentColumnIndex+currentColumnOffset,row:currentRowIndex+currentRowOffset,height:0}));drawTexturedSurface({top:true,ground:true,vertices:currentGroundVertices,points:currentGroundVertices.map(projectBlockVertex)},currentGroundImage)}}
const currentRenderFaces=currentMapRecord.buildings.flatMap(currentBuilding=>currentBuilding.faces.flatMap(splitWallFloors).map(currentFace=>({...currentFace,building:currentBuilding,textureTiles:readBuildingTileSet(currentBuilding),points:currentFace.vertices.map(currentVertex=>projectBlockVertex({column:currentBuilding.origin.column+currentVertex.column,row:currentBuilding.origin.row+currentVertex.row,height:currentVertex.height})),depth:currentFace.vertices.reduce((s,v)=>s+projectBlockVertex({column:currentBuilding.origin.column+v.column,row:currentBuilding.origin.row+v.row}).y,0)/currentFace.vertices.length}))).sort((a,b)=>a.depth-b.depth);
for(const currentFace of currentRenderFaces){const currentAreaValue=currentFace.points.reduce((s,p,i)=>{const n=currentFace.points[(i+1)%currentFace.points.length];return s+p.x*n.y-n.x*p.y},0);if(currentFace.top||currentAreaValue>0){drawSurfacePolygon(currentFace.points,currentMaterialColors[currentFace.material]);// 지붕 경사 측면은 막힌 벽으로 두고 일반 벽 구간에만 창문을 교차 배치한다.
const currentTextureRole=selectWallTexture(currentFace);
const currentTextureName=currentFace.textureTiles[currentTextureRole];drawTexturedSurface(currentFace,loadedTextureImages[currentTextureName])}}
// 타일을 입힌 뒤 실제 블록의 노출 경계를 다시 그린다. 층별 텍스처 분할선은 제외한다.
if(document.querySelector('#edges').checked){
 for(const currentBuildingRecord of currentMapRecord.buildings)for(const currentOriginalFace of currentBuildingRecord.faces){
  const currentOutlinePoints=currentOriginalFace.vertices.map(currentVertexPoint=>projectBlockVertex({column:currentBuildingRecord.origin.column+currentVertexPoint.column,row:currentBuildingRecord.origin.row+currentVertexPoint.row,height:currentVertexPoint.height}));
  const currentOutlineArea=currentOutlinePoints.reduce((currentAreaSum,currentPointValue,currentPointIndex)=>{const nextPointValue=currentOutlinePoints[(currentPointIndex+1)%currentOutlinePoints.length];return currentAreaSum+currentPointValue.x*nextPointValue.y-nextPointValue.x*currentPointValue.y},0);
  if(!currentOriginalFace.top&&currentOutlineArea<=0)continue;
  currentDrawingContext.beginPath();currentOutlinePoints.forEach((currentPointValue,currentPointIndex)=>currentPointIndex?currentDrawingContext.lineTo(currentPointValue.x,currentPointValue.y):currentDrawingContext.moveTo(currentPointValue.x,currentPointValue.y));currentDrawingContext.closePath();currentDrawingContext.strokeStyle=BLOCK_BOUNDARY_COLOR;currentDrawingContext.lineWidth=1/currentScaleValue;currentDrawingContext.stroke();
 }
}
const currentMarkerPoint=projectBlockVertex(currentCharacterCell);if(document.querySelector('#show-character').checked){const characterScaleValue=reviewCharacterRecord.displayHeight/reviewCharacterRecord.bodyHeight,characterFrameRect=reviewCharacterRecord.frame.rect,characterAnchorPoint=reviewCharacterRecord.frame.anchor;currentDrawingContext.drawImage(reviewCharacterImage,characterFrameRect.x,characterFrameRect.y,characterFrameRect.width,characterFrameRect.height,currentMarkerPoint.x-characterAnchorPoint.x*characterScaleValue,currentMarkerPoint.y-characterAnchorPoint.y*characterScaleValue,characterFrameRect.width*characterScaleValue,characterFrameRect.height*characterScaleValue);} currentDrawingContext.setTransform(1,0,0,1,0,0);const currentBuildingFloorSummary=[...new Set(currentMapRecord.buildings.map(currentBuildingRecord=>currentBuildingRecord.floors))].sort((firstFloorCount,secondFloorCount)=>firstFloorCount-secondFloorCount).map(currentFloorCount=>`${currentFloorCount}층 ${currentMapRecord.buildings.filter(currentBuildingRecord=>currentBuildingRecord.floors===currentFloorCount).length}개`).join(' · '),currentRoofHeightValues=[...new Set(currentMapRecord.buildings.flatMap(currentBuildingRecord=>currentBuildingRecord.blocks).filter(currentBlockRecord=>currentBlockRecord.material==='roof').map(currentBlockRecord=>currentBlockRecord.height))].sort((firstHeightValue,secondHeightValue)=>firstHeightValue-secondHeightValue),currentRoofHeightSummary=currentRoofHeightValues.join('·');document.querySelector('#status').textContent=`회전 ${currentCameraRotation*90}° · 건물 ${currentMapRecord.buildings.length}개 (${currentBuildingFloorSummary}) · 블록 ${currentMapRecord.buildings.reduce((s,b)=>s+b.blocks.length,0)}개 · 일반 블록 ${TOWN_BLOCK_HEIGHT}px · 지붕 경사 ${currentRoofHeightSummary}px · 사람 높이 ${gameRenderMetrics.characterHeight} · 마을 타일 ${gameRenderMetrics.townTileWidth}×${gameRenderMetrics.townTileHeight} · 지붕 보행 불가`}
currentMapRecord.buildings.forEach(currentBuilding=>{const currentOption=document.createElement('option');currentOption.value=currentBuilding.id;currentOption.textContent=currentBuilding.name;document.querySelector('#building').append(currentOption)});
document.querySelector('#building').onchange=currentEvent=>{const currentBuilding=currentMapRecord.buildings.find(b=>b.id===currentEvent.target.value);if(!currentBuilding)return;const currentCenter=projectBlockVertex({column:currentBuilding.origin.column+currentBuilding.width/2-.5,row:currentBuilding.origin.row+currentBuilding.height/2-.5,height:TOWN_BLOCK_HEIGHT});currentScaleValue=1;currentOffsetX=currentMapCanvas.width/2-currentCenter.x;currentOffsetY=currentMapCanvas.height/2-currentCenter.y;renderBlockMap()};
document.querySelector('#rotate').onclick=()=>{currentCameraRotation=(currentCameraRotation+1)%4;renderBlockMap(true)};document.querySelector('#fit').onclick=()=>renderBlockMap(true);document.querySelector('#edges').onchange=()=>renderBlockMap();window.onresize=()=>centerCharacterView();
currentMapCanvas.onclick=currentEvent=>{if(suppressMarkerClick){suppressMarkerClick=false;return;}const currentBounds=currentMapCanvas.getBoundingClientRect(),currentWorldX=(currentEvent.clientX-currentBounds.left-currentOffsetX)/currentScaleValue,currentWorldY=(currentEvent.clientY-currentBounds.top-currentOffsetY)/currentScaleValue;let currentColumnValue=(currentWorldX/townHalfTileWidth+currentWorldY/townHalfTileHeight)/2,currentRowValue=(currentWorldY/townHalfTileHeight-currentWorldX/townHalfTileWidth)/2;for(let i=0;i<currentCameraRotation;i++)[currentColumnValue,currentRowValue]=[currentRowValue,-currentColumnValue];currentColumnValue=Math.round(currentColumnValue);currentRowValue=Math.round(currentRowValue);if(currentColumnValue<0||currentColumnValue>=currentMapRecord.columns||currentRowValue<0||currentRowValue>=currentMapRecord.rows||currentBlockedCells.has(`${currentColumnValue},${currentRowValue}`))return;currentCharacterCell={column:currentColumnValue,row:currentRowValue};renderBlockMap()};centerCharacterView();

// 포인터 아래의 지형 좌표를 유지하면서 배율을 변경한다.
function changeMapZoom(currentZoomFactor,currentAnchorX=currentMapCanvas.width/2,currentAnchorY=currentMapCanvas.height/2){
 const nextScaleValue=Math.max(MIN_MAP_SCALE,Math.min(MAX_MAP_SCALE,currentScaleValue*currentZoomFactor));
 currentOffsetX=currentAnchorX-(currentAnchorX-currentOffsetX)*nextScaleValue/currentScaleValue;
 currentOffsetY=currentAnchorY-(currentAnchorY-currentOffsetY)*nextScaleValue/currentScaleValue;
 currentScaleValue=nextScaleValue;renderBlockMap();
}
document.querySelector('#zoom-in').onclick=()=>changeMapZoom(MAP_ZOOM_FACTOR);
document.querySelector('#zoom-out').onclick=()=>changeMapZoom(1/MAP_ZOOM_FACTOR);
currentMapCanvas.onkeydown=currentKeyboardEvent=>{
 const mapKeyboardMoveByKey={ArrowLeft:[MAP_KEYBOARD_PAN_DISTANCE,0],ArrowRight:[-MAP_KEYBOARD_PAN_DISTANCE,0],ArrowUp:[0,MAP_KEYBOARD_PAN_DISTANCE],ArrowDown:[0,-MAP_KEYBOARD_PAN_DISTANCE]}[currentKeyboardEvent.key];
 if(mapKeyboardMoveByKey){currentKeyboardEvent.preventDefault();currentOffsetX+=mapKeyboardMoveByKey[0];currentOffsetY+=mapKeyboardMoveByKey[1];renderBlockMap();return}
 if(currentKeyboardEvent.key==='+'||currentKeyboardEvent.key==='='){currentKeyboardEvent.preventDefault();changeMapZoom(MAP_ZOOM_FACTOR);return}
 if(currentKeyboardEvent.key==='-'){currentKeyboardEvent.preventDefault();changeMapZoom(1/MAP_ZOOM_FACTOR);return}
 if(currentKeyboardEvent.key==='0'){currentKeyboardEvent.preventDefault();renderBlockMap(true)}
};
currentMapCanvas.addEventListener('wheel',currentPointerEvent=>{currentPointerEvent.preventDefault();const currentCanvasBounds=currentMapCanvas.getBoundingClientRect();changeMapZoom(Math.exp(-Math.max(-100,Math.min(100,currentPointerEvent.deltaY))*0.002),currentPointerEvent.clientX-currentCanvasBounds.left,currentPointerEvent.clientY-currentCanvasBounds.top)},{passive:false});
currentMapCanvas.onpointerdown=currentPointerEvent=>{if(currentPointerEvent.button!==0)return;suppressMarkerClick=false;activeMapPointer={id:currentPointerEvent.pointerId,x:currentPointerEvent.clientX,y:currentPointerEvent.clientY,offsetX:currentOffsetX,offsetY:currentOffsetY};currentMapCanvas.setPointerCapture(currentPointerEvent.pointerId)};
currentMapCanvas.onpointermove=currentPointerEvent=>{if(!activeMapPointer||activeMapPointer.id!==currentPointerEvent.pointerId)return;const currentDeltaX=currentPointerEvent.clientX-activeMapPointer.x,currentDeltaY=currentPointerEvent.clientY-activeMapPointer.y;if(!suppressMarkerClick&&Math.hypot(currentDeltaX,currentDeltaY)<MAP_DRAG_THRESHOLD)return;suppressMarkerClick=true;currentMapCanvas.style.cursor='grabbing';currentOffsetX=activeMapPointer.offsetX+currentDeltaX;currentOffsetY=activeMapPointer.offsetY+currentDeltaY;renderBlockMap()};
function finishMapDrag(){activeMapPointer=null;currentMapCanvas.style.cursor='grab'}
currentMapCanvas.onpointerup=finishMapDrag;currentMapCanvas.onpointercancel=finishMapDrag;currentMapCanvas.onlostpointercapture=finishMapDrag;

document.querySelector('#show-character').onchange=()=>renderBlockMap();

function centerCharacterView(){
 currentScaleValue=gameRenderMetrics.defaultZoom;
 const currentCharacterPoint=projectBlockVertex(currentCharacterCell);
 currentOffsetX=currentMapCanvas.clientWidth/2-currentCharacterPoint.x*currentScaleValue;
 currentOffsetY=currentMapCanvas.clientHeight/2-(currentCharacterPoint.y-reviewCharacterRecord.displayHeight/2)*currentScaleValue;
 renderBlockMap();
}
document.querySelector('#actual-size').onclick=centerCharacterView;
