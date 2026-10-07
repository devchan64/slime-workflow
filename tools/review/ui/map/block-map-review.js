import {createFieldReviewFrame,pickFieldReviewCell} from './field-map-renderer.js';
import {FIELD_RENDER_METRICS,projectSurfaceCell} from './vendor/field-surface/1.0.5/field-surface.mjs';
import {resolveFieldActorContactShadow} from './vendor/field-renderer/1.0.6/field-renderer.mjs';
const MIN_MAP_SCALE=0.05,MAX_MAP_SCALE=4,MAP_ZOOM_FACTOR=1.25,MAP_DRAG_THRESHOLD=4,MAP_KEYBOARD_PAN_DISTANCE=48;
let activeMapPointer=null,suppressMarkerClick=false;
const currentMapCanvas=document.querySelector('#map');
async function fetchMapReviewRecord(currentFilePath){const currentFetchResponse=await fetch(new URL(currentFilePath,import.meta.url),{cache:'no-store'});if(!currentFetchResponse.ok)throw Error(`맵 데이터 로드 실패: ${currentFilePath}`);return currentFetchResponse.json()}
const gameRenderMetrics=await fetchMapReviewRecord('game-render-metrics.json');
const blockRenderProfile=await fetchMapReviewRecord('block-render-profile.json');
const TOWN_BLOCK_HEIGHT=blockRenderProfile.blockHeight;
const BLOCK_BOUNDARY_COLOR='#dce5ef';
if(!Number.isInteger(TOWN_BLOCK_HEIGHT)||TOWN_BLOCK_HEIGHT<=0)throw Error('마을 블록 높이 설정이 올바르지 않습니다.');
const townHalfTileWidth=gameRenderMetrics.townTileWidth/2,townHalfTileHeight=gameRenderMetrics.townTileHeight/2;
const availableMapRecords=await fetchMapReviewRecord('block-map-index.json');
const isCharacterReviewPage=currentMapCanvas.dataset.characterReview==='true';
const CHARACTER_REVIEW_RESOLUTION_SCALE=isCharacterReviewPage?2:1;
const CHARACTER_REVIEW_GRID_SIZE=3;
const CHARACTER_REVIEW_TILE_NAMES=['paving','grass','meadow-road'];
const selectedMapIdentifier=new URLSearchParams(location.search).get('map')||availableMapRecords[0].id;
const isTownSpecificReviewPage=new URLSearchParams(location.search).get('townPage')==='1';
const selectedMapRecord=availableMapRecords.find(currentMapEntry=>currentMapEntry.id===selectedMapIdentifier);
if(!selectedMapRecord){document.querySelector('#status').textContent='등록되지 않은 맵입니다.';throw Error('등록되지 않은 맵: '+selectedMapIdentifier)}
function selectReviewMap(currentMapIdentifier){
 if(!availableMapRecords.some(currentMapEntry=>currentMapEntry.id===currentMapIdentifier))throw Error('등록된 맵을 선택하세요.');
 const selectedMapUrl=new URL(location.href);selectedMapUrl.searchParams.set('map',currentMapIdentifier);location.assign(selectedMapUrl);
}
const currentMapSelector=document.querySelector('#map-select');
if(currentMapSelector){
 for(const currentMapEntry of availableMapRecords)currentMapSelector.append(new Option(currentMapEntry.name,currentMapEntry.id));
 currentMapSelector.value=selectedMapIdentifier;
 if(isTownSpecificReviewPage){currentMapSelector.closest('label').hidden=true;document.querySelector('#load-map').hidden=true;}
 document.querySelector('#load-map').onclick=()=>selectReviewMap(currentMapSelector.value);
}
const GROUND_CONTRAST_PREVIEW_VALUES={original:1,soft:0.65};
let currentGroundPreviewMode='original';
let currentOutlinePreviewEnabled=true;
let currentRimPreviewEnabled=true;
let currentShadowPreviewEnabled=true;
let currentCharacterRimCanvas=null;
const CHARACTER_RIM_PREVIEW_COLOR='#fff2cc';
const CHARACTER_RIM_BAND_WIDTH=1;
let currentOutlineBaseWidth=1;
let currentCharacterSilhouetteCanvas=null;
const CHARACTER_OUTLINE_PREVIEW_COLOR=isCharacterReviewPage?'#655d54':'#302a25';
const CHARACTER_CONTACT_SHADOW_COLOR='#242424';
const CHARACTER_CONTACT_SHADOW_SIZE_SCALE=1;
const CHARACTER_CONTACT_SHADOW_ALPHA_SCALE=1.2;
let currentShadowColorOverride=isCharacterReviewPage?CHARACTER_CONTACT_SHADOW_COLOR:null;
const CHARACTER_OUTLINE_PIXEL_OFFSETS=[[-1,0],[1,0],[0,-1],[0,1],[-0.707,-0.707],[0.707,-0.707],[-0.707,0.707],[0.707,0.707]];
const currentDisplayOptions={'show-character':true,'show-safe-boundary':true,edges:false,'shadow-profile':'contrast'};
function readReviewOption(currentOptionName){return document.getElementById(currentOptionName)?.checked??currentDisplayOptions[currentOptionName];}
// 검수용 반복 견본은 게임 맵 원본과 분리하며 등록된 타일·캐릭터만 공유한다.
const currentMapRecord=isCharacterReviewPage?{
 id:'character-review',name:'캐릭터 표현',reviewLabel:'3×3 검수 맵',safeTown:true,
 columns:CHARACTER_REVIEW_GRID_SIZE,rows:CHARACTER_REVIEW_GRID_SIZE,
 terrainCodes:{p:'paving'},terrainRows:Array(CHARACTER_REVIEW_GRID_SIZE).fill('p'.repeat(CHARACTER_REVIEW_GRID_SIZE)),
 startPoint:{column:Math.floor(CHARACTER_REVIEW_GRID_SIZE/2),row:Math.floor(CHARACTER_REVIEW_GRID_SIZE/2)},blocked:[],buildings:[],
}:await fetchMapReviewRecord(selectedMapRecord.path);
const isFieldMapReview=currentMapRecord.safeTown===false;
const currentDrawingContext=isFieldMapReview?null:currentMapCanvas.getContext('2d');
const currentSafeVisualRecords=isFieldMapReview?await fetchMapReviewRecord('field-safe-visuals.json'):{};
const currentSafeVisualImages={};
await Promise.all(Object.entries(currentSafeVisualRecords).map(([currentVisualName,currentVisualRecord])=>new Promise((resolveVisualImage,rejectVisualImage)=>{
 const currentVisualImage=new Image();currentVisualImage.onload=()=>{currentSafeVisualImages[currentVisualName]=currentVisualImage;resolveVisualImage()};currentVisualImage.onerror=()=>rejectVisualImage(Error('결계 원본 로드 실패: '+currentVisualName));currentVisualImage.src=new URL(currentVisualRecord.image,import.meta.url).href;
})));
if(document.querySelector('#show-safe-boundary'))document.querySelector('#show-safe-boundary').closest('label').hidden=!isFieldMapReview;
const loadedGuardImages={};
await Promise.all((currentMapRecord.guardCenters??[]).map(currentGuardRecord=>new Promise((resolveGuardImage,rejectGuardImage)=>{
 const currentGuardImage=new Image();currentGuardImage.onload=()=>{loadedGuardImages[currentGuardRecord.path]=currentGuardImage;resolveGuardImage()};currentGuardImage.onerror=()=>rejectGuardImage(Error('경비센터 이미지 로드 실패'));currentGuardImage.src=currentGuardRecord.image;
})));
let currentFieldFrame=null;
const currentReviewTitle=currentMapRecord.name+' · '+currentMapRecord.reviewLabel;
document.querySelector('#map-title').textContent=currentReviewTitle;
document.title=currentReviewTitle;
document.querySelector('.map-toolbar')?.setAttribute('aria-label',currentMapRecord.reviewLabel+' 도구');
currentMapCanvas.setAttribute('aria-label',currentReviewTitle+'. 방향키로 이동하고 더하기와 빼기 키로 확대 또는 축소하며 0 키로 전체 보기를 적용합니다.');
const currentMaterialColors=await fetchMapReviewRecord('block-materials.json');
const buildingTileRecords=await fetchMapReviewRecord('block-building-tiles.json');
const currentTextureRecords=await fetchMapReviewRecord('/management/map-assets/textures');
const loadedTextureImages={};
await Promise.all(Object.entries(currentTextureRecords).map(([currentTextureName,currentTextureRecord])=>new Promise((resolveTextureLoad,rejectTextureLoad)=>{const currentTextureImage=new Image();currentTextureImage.onload=()=>{loadedTextureImages[currentTextureName]=currentTextureImage;resolveTextureLoad()};currentTextureImage.onerror=()=>{document.querySelector('#status').textContent='타일 로드 실패: '+currentTextureName;rejectTextureLoad(Error(currentTextureName))};currentTextureImage.src=new URL(currentTextureRecord.path,import.meta.url).href})));
const reviewCharacterRecord=await fetchMapReviewRecord('review-character.json');
const reviewCharacterImage=new Image();
await new Promise((resolveCharacterLoad,rejectCharacterLoad)=>{reviewCharacterImage.onload=resolveCharacterLoad;reviewCharacterImage.onerror=()=>rejectCharacterLoad(Error('기본 캐릭터 로드 실패'));reviewCharacterImage.src=new URL(reviewCharacterRecord.image,import.meta.url).href});
const currentSharedFieldView=isFieldMapReview?await (await import('./field-map-view.js')).createSharedFieldReview(currentMapCanvas,loadedTextureImages,reviewCharacterImage,reviewCharacterRecord,loadedGuardImages,currentSafeVisualImages):null;
if(currentSharedFieldView)window.addEventListener('pagehide',()=>currentSharedFieldView.destroy(),{once:true});
const groundTextureNames={grass:currentMapRecord.id==='iseulon'?'iseulon-grass-mud-frame':'grass',paving:currentMapRecord.id==='stonewarm'?'stonewarm-marble-paving':currentMapRecord.id==='saltford'?'stonewarm-gravel-paving':['reedhaven','grainstead'].includes(currentMapRecord.id)?'reedhaven-dirt-road':'paving',gravel:currentMapRecord.id==='stonewarm'?'stonewarm-exposed-rock-ground':'gravel',flowers:currentMapRecord.id==='meadow'?'grass-type-b':'flower_bed',dew:'dew',ash:'ash',moss:'moss','leaf-litter':'leaf-litter','tree-base':'tree-base',wall:'cliff-wall',stone:'stone','dry-soil-branches':'dry-soil-branches',mud:'mud',boulder:'boulder',cactus:'cactus',road:currentMapRecord.id==='meadow'?'meadow-road':'packed_dirt_road',water:'spring_water','deep-water':'deep-water','shallow-water':'shallow-water','reed-bed':'reed-bed'};
function readBuildingTileSet(currentBuildingRecord){return {...buildingTileRecords['iseulon-'+currentBuildingRecord.facilityKind],...(currentMapRecord.buildingTileOverrides||{}),...(buildingTileRecords[currentBuildingRecord.id]||{})}}
function renderAppliedTileSourceList(){
 const appliedTextureNames=new Set(isFieldMapReview?['cliff-wall','ramp-tread']:[]);
 Object.values(currentMapRecord.terrainCodes).forEach(currentTerrainName=>{const currentTextureName=groundTextureNames[currentTerrainName];if(currentTextureName)appliedTextureNames.add(currentTextureName)});
 currentMapRecord.buildings.forEach(currentBuildingRecord=>Object.values(readBuildingTileSet(currentBuildingRecord)).forEach(currentTextureName=>appliedTextureNames.add(currentTextureName)));
 const appliedTileList=document.querySelector('#applied-tile-list');appliedTileList.replaceChildren();
 for(const [currentVisualName,currentVisualRecord] of Object.entries(currentSafeVisualRecords)){
  const currentVisualItem=document.createElement('li'),currentVisualThumbnail=document.createElement('img'),currentVisualLabel=document.createElement('span');
  currentVisualThumbnail.width=42;currentVisualThumbnail.height=42;currentVisualThumbnail.src=new URL(currentVisualRecord.image,import.meta.url).href;currentVisualThumbnail.alt=currentVisualName==='tower'?'결계탑 원본':'결계 오러 원본';
  currentVisualLabel.textContent=currentVisualThumbnail.alt+' · '+currentVisualRecord.sourceSize.join('×');
  currentVisualItem.title=`${currentVisualRecord.provenance.managementId} · ${currentVisualRecord.provenance.version} · SHA-256 ${currentVisualRecord.provenance.sha256}`;
  currentVisualItem.append(currentVisualThumbnail,currentVisualLabel);appliedTileList.append(currentVisualItem);
 }
 [...appliedTextureNames].sort().forEach(currentTextureName=>{
  const currentTextureRecord=currentTextureRecords[currentTextureName];const currentListItem=document.createElement('li');const currentName=document.createElement('strong');currentName.textContent=currentTextureName;currentListItem.append(currentName);
  if(!currentTextureRecord){const currentWarning=document.createElement('span');currentWarning.className='tile-source-warning';currentWarning.textContent='⚠ 원본 미등록';currentWarning.title='타일 카탈로그에 원본 파일이 등록되지 않았습니다.';currentListItem.append(currentWarning);appliedTileList.append(currentListItem);return}
  const currentThumbnail=document.createElement('img');currentThumbnail.width=42;currentThumbnail.height=42;currentThumbnail.src=new URL(currentTextureRecord.path,import.meta.url).href;currentThumbnail.alt=`${currentTextureName} 원본 썸네일`;currentThumbnail.loading='lazy';currentListItem.prepend(currentThumbnail);
  const sourceSize=currentTextureRecord.source_size;const expectedSourceSize=currentTextureRecord.expected_source_size;const currentSource=document.createElement('span');currentSource.textContent=`${sourceSize?.join('×')||'?'}px`;currentListItem.append(currentSource);
  const normalizationWarning=currentTextureRecord.normalization_warning||(sourceSize&&expectedSourceSize&&sourceSize.every((currentValue,currentIndex)=>currentValue===expectedSourceSize[currentIndex])?null:`정규화 확인 필요: 기준 ${expectedSourceSize?.join('×')||'256×256'}px`);
  if(normalizationWarning){const currentWarning=document.createElement('span');currentWarning.className='tile-source-warning';currentWarning.textContent='⚠';currentWarning.title=normalizationWarning;const currentDescription=document.createElement('span');currentDescription.className='tile-source-warning-description';currentDescription.textContent=normalizationWarning;currentListItem.append(currentWarning,currentDescription)}
  appliedTileList.append(currentListItem);
 });
 for(const currentGuardRecord of currentMapRecord.guardCenters??[]){
  const currentListItem=document.createElement('li');
  const currentThumbnail=document.createElement('img');currentThumbnail.width=42;currentThumbnail.height=42;currentThumbnail.src=currentGuardRecord.image;currentThumbnail.alt='경비센터 원본';currentThumbnail.loading='lazy';
  const currentName=document.createElement('strong');currentName.textContent=`경비센터 · ${currentGuardRecord.cityId}`;
  const currentSource=document.createElement('span');currentSource.textContent=`${currentGuardRecord.provenance.source} · ${currentGuardRecord.provenance.version}`;
  const currentHashDetail=document.createElement('details');const currentHashSummary=document.createElement('summary');currentHashSummary.textContent='원본 식별자·해시';
  const currentHashText=document.createElement('p');currentHashText.textContent=`${currentGuardRecord.provenance.managementId} · SHA-256 ${currentGuardRecord.provenance.sha256}`;
  currentHashDetail.append(currentHashSummary,currentHashText);currentListItem.append(currentThumbnail,currentName,currentSource,currentHashDetail);appliedTileList.append(currentListItem);
 }
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
function drawSurfacePolygon(currentSurfacePoints,currentFillColor){currentDrawingContext.beginPath();currentSurfacePoints.forEach((currentPointValue,currentPointIndex)=>currentPointIndex?currentDrawingContext.lineTo(currentPointValue.x,currentPointValue.y):currentDrawingContext.moveTo(currentPointValue.x,currentPointValue.y));currentDrawingContext.closePath();currentDrawingContext.fillStyle=currentFillColor;currentDrawingContext.fill();if(readReviewOption('edges')){currentDrawingContext.strokeStyle=BLOCK_BOUNDARY_COLOR;currentDrawingContext.lineWidth=1/currentScaleValue;currentDrawingContext.stroke()}}
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
function drawReviewCharacter(currentMarkerPoint){
 if(!readReviewOption('show-character'))return;
 const characterScaleValue=reviewCharacterRecord.displayHeight/reviewCharacterRecord.bodyHeight,characterFrameRect=reviewCharacterRecord.frame.rect,characterAnchorPoint=reviewCharacterRecord.frame.anchor;
 if(currentShadowPreviewEnabled){
 const currentShadowMetrics=resolveFieldActorContactShadow(currentDisplayOptions['shadow-profile']);
 const currentShadowSizeScale=currentShadowColorOverride===null?1:CHARACTER_CONTACT_SHADOW_SIZE_SCALE;
 const currentShadowAlphaScale=currentShadowColorOverride===null?1:CHARACTER_CONTACT_SHADOW_ALPHA_SCALE;
 const currentShadowColor=currentShadowColorOverride??('#'+currentShadowMetrics.color.toString(16).padStart(6,'0'));
 currentDrawingContext.fillStyle=currentShadowColor;currentDrawingContext.globalAlpha=Math.min(1,currentShadowMetrics.outer.alpha*currentShadowAlphaScale);currentDrawingContext.beginPath();currentDrawingContext.ellipse(currentMarkerPoint.x,currentMarkerPoint.y,currentShadowMetrics.outer.width*currentShadowSizeScale/2,currentShadowMetrics.outer.height*currentShadowSizeScale/2,0,0,Math.PI*2);currentDrawingContext.fill();
 currentDrawingContext.globalAlpha=Math.min(1,currentShadowMetrics.core.alpha*currentShadowAlphaScale);currentDrawingContext.beginPath();currentDrawingContext.ellipse(currentMarkerPoint.x,currentMarkerPoint.y,currentShadowMetrics.core.width*currentShadowSizeScale/2,currentShadowMetrics.core.height*currentShadowSizeScale/2,0,0,Math.PI*2);currentDrawingContext.fill();currentDrawingContext.globalAlpha=1;
 }
 if(currentRimPreviewEnabled){
  if(!currentCharacterRimCanvas){
   currentCharacterRimCanvas=document.createElement('canvas');
   currentCharacterRimCanvas.width=characterFrameRect.width;currentCharacterRimCanvas.height=characterFrameRect.height;
   const currentRimDrawingContext=currentCharacterRimCanvas.getContext('2d');
   currentRimDrawingContext.drawImage(reviewCharacterImage,characterFrameRect.x,characterFrameRect.y,characterFrameRect.width,characterFrameRect.height,0,0,characterFrameRect.width,characterFrameRect.height);
   currentRimDrawingContext.globalCompositeOperation='source-in';currentRimDrawingContext.fillStyle=CHARACTER_RIM_PREVIEW_COLOR;
   currentRimDrawingContext.fillRect(0,0,characterFrameRect.width,characterFrameRect.height);
  }
  // 형태선 바깥의 100% 기준 1px 밝은 띠도 캔버스 배율에 비례해 확대한다.
  for(const [currentOffsetHorizontal,currentOffsetVertical] of CHARACTER_OUTLINE_PIXEL_OFFSETS){
   currentDrawingContext.drawImage(currentCharacterRimCanvas,currentMarkerPoint.x-characterAnchorPoint.x*characterScaleValue+currentOffsetHorizontal*(currentOutlineBaseWidth+CHARACTER_RIM_BAND_WIDTH),currentMarkerPoint.y-characterAnchorPoint.y*characterScaleValue+currentOffsetVertical*(currentOutlineBaseWidth+CHARACTER_RIM_BAND_WIDTH),characterFrameRect.width*characterScaleValue,characterFrameRect.height*characterScaleValue);
  }
 }
 if(currentOutlinePreviewEnabled){
  if(!currentCharacterSilhouetteCanvas){
   currentCharacterSilhouetteCanvas=document.createElement('canvas');
   currentCharacterSilhouetteCanvas.width=characterFrameRect.width;currentCharacterSilhouetteCanvas.height=characterFrameRect.height;
   const currentSilhouetteContext=currentCharacterSilhouetteCanvas.getContext('2d');
   currentSilhouetteContext.drawImage(reviewCharacterImage,characterFrameRect.x,characterFrameRect.y,characterFrameRect.width,characterFrameRect.height,0,0,characterFrameRect.width,characterFrameRect.height);
   currentSilhouetteContext.globalCompositeOperation='source-in';currentSilhouetteContext.fillStyle=CHARACTER_OUTLINE_PREVIEW_COLOR;
   currentSilhouetteContext.fillRect(0,0,characterFrameRect.width,characterFrameRect.height);
  }
  // 100% 기준 폭을 사용하고 캔버스 변환으로 캐릭터와 함께 선형 확대한다.
  for(const [currentOffsetHorizontal,currentOffsetVertical] of CHARACTER_OUTLINE_PIXEL_OFFSETS){
   currentDrawingContext.drawImage(currentCharacterSilhouetteCanvas,currentMarkerPoint.x-characterAnchorPoint.x*characterScaleValue+currentOffsetHorizontal*currentOutlineBaseWidth,currentMarkerPoint.y-characterAnchorPoint.y*characterScaleValue+currentOffsetVertical*currentOutlineBaseWidth,characterFrameRect.width*characterScaleValue,characterFrameRect.height*characterScaleValue);
  }
 }
 currentDrawingContext.drawImage(reviewCharacterImage,characterFrameRect.x,characterFrameRect.y,characterFrameRect.width,characterFrameRect.height,currentMarkerPoint.x-characterAnchorPoint.x*characterScaleValue,currentMarkerPoint.y-characterAnchorPoint.y*characterScaleValue,characterFrameRect.width*characterScaleValue,characterFrameRect.height*characterScaleValue);
}
function projectReviewCharacter(){return isFieldMapReview?projectSurfaceCell(currentCharacterCell,currentMapRecord,{...FIELD_RENDER_METRICS,rotation:currentCameraRotation}):projectBlockVertex(currentCharacterCell)}
function renderBlockMap(currentFitRequested=false){
 if(!isCharacterReviewPage){drawCurrentMapScene(currentFitRequested);return;}
 const currentSavedOutline=currentOutlinePreviewEnabled,currentSavedRim=currentRimPreviewEnabled;
 const currentSavedShadow=currentDisplayOptions['shadow-profile'];
 const currentSavedShadowEnabled=currentShadowPreviewEnabled;
 const currentSavedShadowColor=currentShadowColorOverride;
 const currentComparisonCanvas=document.querySelector('#character-baseline-map');
 try{
  currentOutlinePreviewEnabled=false;currentRimPreviewEnabled=false;currentShadowPreviewEnabled=true;currentShadowColorOverride=null;currentDisplayOptions['shadow-profile']='baseline';
  drawCurrentMapScene(currentFitRequested);
  currentComparisonCanvas.width=currentMapCanvas.width;currentComparisonCanvas.height=currentMapCanvas.height;
  currentComparisonCanvas.getContext('2d').drawImage(currentMapCanvas,0,0);
 }finally{
  currentOutlinePreviewEnabled=currentSavedOutline;currentRimPreviewEnabled=currentSavedRim;
  currentDisplayOptions['shadow-profile']=currentSavedShadow;currentShadowPreviewEnabled=currentSavedShadowEnabled;currentShadowColorOverride=currentSavedShadowColor;
 }
 drawCurrentMapScene(false);
 document.querySelector('#status').textContent=`3×3 검수 맵 · 캐릭터 (${currentCharacterCell.column+1}, ${currentCharacterCell.row+1}) · 사람 높이 ${gameRenderMetrics.characterHeight}px · 양쪽 동일 위치·크기 · 원본은 외곽선 없음·기본 접지 그림자`;
}
function drawCurrentMapScene(currentFitRequested=false){
 if(isFieldMapReview){renderSharedFieldMap(currentFitRequested);return;}
currentMapCanvas.width=currentMapCanvas.clientWidth*CHARACTER_REVIEW_RESOLUTION_SCALE;currentMapCanvas.height=currentMapCanvas.clientHeight*CHARACTER_REVIEW_RESOLUTION_SCALE;const currentAllCorners=isFieldMapReview?currentFieldFrame.points:[{column:0,row:0},{column:currentMapRecord.columns,row:0},{column:0,row:currentMapRecord.rows},{column:currentMapRecord.columns,row:currentMapRecord.rows}].map(projectBlockVertex);if(currentFitRequested){const currentMinX=Math.min(...currentAllCorners.map(p=>p.x)),currentMaxX=Math.max(...currentAllCorners.map(p=>p.x)),currentMinY=Math.min(...currentAllCorners.map(p=>p.y))-TOWN_BLOCK_HEIGHT*2,currentMaxY=Math.max(...currentAllCorners.map(p=>p.y))+40;currentScaleValue=Math.min(currentMapCanvas.clientWidth/(currentMaxX-currentMinX+160),currentMapCanvas.clientHeight/(currentMaxY-currentMinY+80));currentOffsetX=currentMapCanvas.clientWidth/2-(currentMinX+currentMaxX)/2*currentScaleValue;currentOffsetY=currentMapCanvas.clientHeight/2-(currentMinY+currentMaxY)/2*currentScaleValue}
document.querySelector('#zoom-level').textContent=Math.round(currentScaleValue*100)+'%';
if(document.querySelector('#zoom-in'))document.querySelector('#zoom-in').disabled=currentScaleValue>=MAX_MAP_SCALE;if(document.querySelector('#zoom-out'))document.querySelector('#zoom-out').disabled=currentScaleValue<=MIN_MAP_SCALE;
currentDrawingContext.setTransform(currentScaleValue*CHARACTER_REVIEW_RESOLUTION_SCALE,0,0,currentScaleValue*CHARACTER_REVIEW_RESOLUTION_SCALE,currentOffsetX*CHARACTER_REVIEW_RESOLUTION_SCALE,currentOffsetY*CHARACTER_REVIEW_RESOLUTION_SCALE);
currentDrawingContext.filter=`contrast(${GROUND_CONTRAST_PREVIEW_VALUES[currentGroundPreviewMode]})`;
for(let currentRowIndex=0;currentRowIndex<currentMapRecord.rows;currentRowIndex++)for(let currentColumnIndex=0;currentColumnIndex<currentMapRecord.columns;currentColumnIndex++){const currentTerrainName=currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentRowIndex][currentColumnIndex]];drawSurfacePolygon([[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]].map(([c,r])=>projectBlockVertex({column:currentColumnIndex+c,row:currentRowIndex+r})),currentMaterialColors[currentTerrainName]);const currentGroundImage=loadedTextureImages[groundTextureNames[currentTerrainName]];if(currentGroundImage){const currentGroundVertices=[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]].map(([currentColumnOffset,currentRowOffset])=>({column:currentColumnIndex+currentColumnOffset,row:currentRowIndex+currentRowOffset,height:0}));drawTexturedSurface({top:true,ground:true,vertices:currentGroundVertices,points:currentGroundVertices.map(projectBlockVertex)},currentGroundImage)}}
currentDrawingContext.filter='none';
const currentRenderFaces=currentMapRecord.buildings.flatMap(currentBuilding=>currentBuilding.faces.flatMap(splitWallFloors).map(currentFace=>({...currentFace,building:currentBuilding,textureTiles:readBuildingTileSet(currentBuilding),points:currentFace.vertices.map(currentVertex=>projectBlockVertex({column:currentBuilding.origin.column+currentVertex.column,row:currentBuilding.origin.row+currentVertex.row,height:currentVertex.height})),depth:currentFace.vertices.reduce((s,v)=>s+projectBlockVertex({column:currentBuilding.origin.column+v.column,row:currentBuilding.origin.row+v.row}).y,0)/currentFace.vertices.length}))).sort((a,b)=>a.depth-b.depth);
for(const currentFace of currentRenderFaces){const currentAreaValue=currentFace.points.reduce((s,p,i)=>{const n=currentFace.points[(i+1)%currentFace.points.length];return s+p.x*n.y-n.x*p.y},0);if(currentFace.top||currentAreaValue>0){drawSurfacePolygon(currentFace.points,currentMaterialColors[currentFace.material]);// 지붕 경사 측면은 막힌 벽으로 두고 일반 벽 구간에만 창문을 교차 배치한다.
const currentTextureRole=selectWallTexture(currentFace);
const currentTextureName=currentFace.textureTiles[currentTextureRole];drawTexturedSurface(currentFace,loadedTextureImages[currentTextureName])}}
// 타일을 입힌 뒤 실제 블록의 노출 경계를 다시 그린다. 층별 텍스처 분할선은 제외한다.
if(readReviewOption('edges')){
 for(const currentBuildingRecord of currentMapRecord.buildings)for(const currentOriginalFace of currentBuildingRecord.faces){
  const currentOutlinePoints=currentOriginalFace.vertices.map(currentVertexPoint=>projectBlockVertex({column:currentBuildingRecord.origin.column+currentVertexPoint.column,row:currentBuildingRecord.origin.row+currentVertexPoint.row,height:currentVertexPoint.height}));
  const currentOutlineArea=currentOutlinePoints.reduce((currentAreaSum,currentPointValue,currentPointIndex)=>{const nextPointValue=currentOutlinePoints[(currentPointIndex+1)%currentOutlinePoints.length];return currentAreaSum+currentPointValue.x*nextPointValue.y-nextPointValue.x*currentPointValue.y},0);
  if(!currentOriginalFace.top&&currentOutlineArea<=0)continue;
  currentDrawingContext.beginPath();currentOutlinePoints.forEach((currentPointValue,currentPointIndex)=>currentPointIndex?currentDrawingContext.lineTo(currentPointValue.x,currentPointValue.y):currentDrawingContext.moveTo(currentPointValue.x,currentPointValue.y));currentDrawingContext.closePath();currentDrawingContext.strokeStyle=BLOCK_BOUNDARY_COLOR;currentDrawingContext.lineWidth=1/currentScaleValue;currentDrawingContext.stroke();
 }
}
if(!isFieldMapReview)drawReviewCharacter(projectReviewCharacter()); currentDrawingContext.setTransform(1,0,0,1,0,0);const currentBuildingFloorSummary=[...new Set(currentMapRecord.buildings.map(currentBuildingRecord=>currentBuildingRecord.floors))].sort((firstFloorCount,secondFloorCount)=>firstFloorCount-secondFloorCount).map(currentFloorCount=>`${currentFloorCount}층 ${currentMapRecord.buildings.filter(currentBuildingRecord=>currentBuildingRecord.floors===currentFloorCount).length}개`).join(' · '),currentRoofHeightValues=[...new Set(currentMapRecord.buildings.flatMap(currentBuildingRecord=>currentBuildingRecord.blocks).filter(currentBlockRecord=>currentBlockRecord.material==='roof').map(currentBlockRecord=>currentBlockRecord.height))].sort((firstHeightValue,secondHeightValue)=>firstHeightValue-secondHeightValue),currentRoofHeightSummary=currentRoofHeightValues.join('·');document.querySelector('#status').textContent=isFieldMapReview?`필드 고도 ${Math.min(...currentMapRecord.elevations.flat())}–${Math.max(...currentMapRecord.elevations.flat())} · 높이 단위 ${FIELD_RENDER_METRICS.elevationHeight}px · 타일 ${FIELD_RENDER_METRICS.tileWidth}×${FIELD_RENDER_METRICS.tileHeight} · 계단 ${currentMapRecord.elevationTiles.length}개 · 회전 ${currentCameraRotation*90}°`:`회전 ${currentCameraRotation*90}° · 건물 ${currentMapRecord.buildings.length}개 (${currentBuildingFloorSummary}) · 블록 ${currentMapRecord.buildings.reduce((s,b)=>s+b.blocks.length,0)}개 · 일반 블록 ${TOWN_BLOCK_HEIGHT}px · 지붕 경사 ${currentRoofHeightSummary}px · 사람 높이 ${gameRenderMetrics.characterHeight} · 마을 타일 ${gameRenderMetrics.townTileWidth}×${gameRenderMetrics.townTileHeight} · 지붕 보행 불가`}
function renderSharedFieldMap(currentFitRequested){
 if(!currentFieldFrame||currentFieldFrame.options.rotation!==currentCameraRotation)currentFieldFrame=createFieldReviewFrame(currentMapRecord,currentCameraRotation);
 if(currentFitRequested){
  const currentMinimumX=Math.min(...currentFieldFrame.points.map(currentPointValue=>currentPointValue.x)),currentMaximumX=Math.max(...currentFieldFrame.points.map(currentPointValue=>currentPointValue.x));
  const currentMinimumY=Math.min(...currentFieldFrame.points.map(currentPointValue=>currentPointValue.y))-160,currentMaximumY=Math.max(...currentFieldFrame.points.map(currentPointValue=>currentPointValue.y))+40;
  currentScaleValue=Math.min(currentMapCanvas.clientWidth/(currentMaximumX-currentMinimumX+160),currentMapCanvas.clientHeight/(currentMaximumY-currentMinimumY+80));
  currentOffsetX=currentMapCanvas.clientWidth/2-(currentMinimumX+currentMaximumX)/2*currentScaleValue;currentOffsetY=currentMapCanvas.clientHeight/2-(currentMinimumY+currentMaximumY)/2*currentScaleValue;
 }
 document.querySelector('#zoom-level').textContent=Math.round(currentScaleValue*100)+'%';
 if(document.querySelector('#zoom-in'))document.querySelector('#zoom-in').disabled=currentScaleValue>=MAX_MAP_SCALE;if(document.querySelector('#zoom-out'))document.querySelector('#zoom-out').disabled=currentScaleValue<=MIN_MAP_SCALE;
 currentSharedFieldView.render(currentFieldFrame,currentMapRecord,groundTextureNames,{scale:currentScaleValue,offsetX:currentOffsetX,offsetY:currentOffsetY,edges:readReviewOption('edges'),safe:readReviewOption('show-safe-boundary'),character:readReviewOption('show-character'),characterCell:currentCharacterCell,shadowProfile:currentDisplayOptions['shadow-profile']});
 document.querySelector('#status').textContent=`게임 공용 필드 렌더러 · 내부 해상도 2배 · 높이 단위 ${FIELD_RENDER_METRICS.elevationHeight}px · 타일 ${FIELD_RENDER_METRICS.tileWidth}×${FIELD_RENDER_METRICS.tileHeight} · 결계 높이 15px · 회전 ${currentCameraRotation*90}°`;
}
if(document.querySelector('#show-safe-boundary'))document.querySelector('#show-safe-boundary').onchange=()=>renderBlockMap();
function focusReviewBuilding(currentBuildingIdentifier){
 const currentBuilding=currentMapRecord.buildings.find(currentBuildingEntry=>currentBuildingEntry.id===currentBuildingIdentifier);
 if(!currentBuilding)throw Error('검수할 건물을 선택하세요.');
 const currentCenter=projectBlockVertex({column:currentBuilding.origin.column+currentBuilding.width/2-.5,row:currentBuilding.origin.row+currentBuilding.height/2-.5,height:TOWN_BLOCK_HEIGHT});
 currentScaleValue=1;currentOffsetX=currentMapCanvas.clientWidth/2-currentCenter.x;currentOffsetY=currentMapCanvas.clientHeight/2-currentCenter.y;renderBlockMap();
}
const currentBuildingSelector=document.querySelector('#building');
if(currentBuildingSelector){
 if(isFieldMapReview)currentBuildingSelector.closest('section').hidden=true;
 currentMapRecord.buildings.forEach(currentBuilding=>currentBuildingSelector.append(new Option(currentBuilding.name,currentBuilding.id)));
 currentBuildingSelector.onchange=currentEvent=>{if(currentEvent.target.value)focusReviewBuilding(currentEvent.target.value);};
}
if(document.querySelector('#edges'))document.querySelector('#edges').onchange=()=>renderBlockMap();window.onresize=()=>renderBlockMap();
currentMapCanvas.onclick=currentEvent=>{if(suppressMarkerClick){suppressMarkerClick=false;return;}const currentBounds=currentMapCanvas.getBoundingClientRect(),currentWorldX=(currentEvent.clientX-currentBounds.left-currentOffsetX)/currentScaleValue,currentWorldY=(currentEvent.clientY-currentBounds.top-currentOffsetY)/currentScaleValue;if(isFieldMapReview){const currentPickedCell=pickFieldReviewCell({x:currentWorldX,y:currentWorldY},currentFieldFrame);if(currentPickedCell&&!currentBlockedCells.has(`${currentPickedCell.column},${currentPickedCell.row}`)){currentCharacterCell=currentPickedCell;renderBlockMap();}return;}let currentColumnValue=(currentWorldX/townHalfTileWidth+currentWorldY/townHalfTileHeight)/2,currentRowValue=(currentWorldY/townHalfTileHeight-currentWorldX/townHalfTileWidth)/2;for(let i=0;i<currentCameraRotation;i++)[currentColumnValue,currentRowValue]=[currentRowValue,-currentColumnValue];currentColumnValue=Math.round(currentColumnValue);currentRowValue=Math.round(currentRowValue);if(currentColumnValue<0||currentColumnValue>=currentMapRecord.columns||currentRowValue<0||currentRowValue>=currentMapRecord.rows||currentBlockedCells.has(`${currentColumnValue},${currentRowValue}`))return;currentCharacterCell={column:currentColumnValue,row:currentRowValue};renderBlockMap()};centerCharacterView();

// 포인터 아래의 지형 좌표를 유지하면서 배율을 변경한다.
function changeMapZoom(currentZoomFactor,currentAnchorX=currentMapCanvas.clientWidth/2,currentAnchorY=currentMapCanvas.clientHeight/2){
 const nextScaleValue=Math.max(MIN_MAP_SCALE,Math.min(MAX_MAP_SCALE,currentScaleValue*currentZoomFactor));
 currentOffsetX=currentAnchorX-(currentAnchorX-currentOffsetX)*nextScaleValue/currentScaleValue;
 currentOffsetY=currentAnchorY-(currentAnchorY-currentOffsetY)*nextScaleValue/currentScaleValue;
 currentScaleValue=nextScaleValue;renderBlockMap();
}

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

if(document.querySelector('#show-character'))document.querySelector('#show-character').onchange=()=>renderBlockMap();
if(document.querySelector('#actor-shadow-profile'))document.querySelector('#actor-shadow-profile').onchange=currentEvent=>window.mapReviewDisplayOptions(readReviewOption('show-character'),readReviewOption('show-safe-boundary'),readReviewOption('edges'),currentEvent.target.value);

function centerCharacterView(){
 currentScaleValue=isCharacterReviewPage?1:gameRenderMetrics.defaultZoom;
 const currentCharacterPoint=projectReviewCharacter();
 currentOffsetX=currentMapCanvas.clientWidth/2-currentCharacterPoint.x*currentScaleValue;
 currentOffsetY=currentMapCanvas.clientHeight/2-(currentCharacterPoint.y-reviewCharacterRecord.displayHeight/2)*currentScaleValue;
 renderBlockMap();
}
// 기본 HTML과 Gradio가 동일한 브라우저 카메라 명령을 사용한다.
const currentCameraActions={
 'rotate':()=>{currentCameraRotation=(currentCameraRotation+1)%4;renderBlockMap(true);},
 'fit':()=>renderBlockMap(true),
 'zoom-in':()=>changeMapZoom(MAP_ZOOM_FACTOR),
 'zoom-out':()=>changeMapZoom(1/MAP_ZOOM_FACTOR),
 'actual-size':()=>{centerCharacterView();changeMapZoom(1/currentScaleValue);},
};
window.mapReviewCameraControls=(currentActionName)=>{
 if(!Object.hasOwn(currentCameraActions,currentActionName))throw Error('지원하지 않는 맵 시점 명령입니다.');
 currentCameraActions[currentActionName]();
 return `회전 ${currentCameraRotation*90}° · 확대 ${Math.round(currentScaleValue*100)}%`;
};
for(const currentActionName of Object.keys(currentCameraActions)){
 const currentActionElement=document.getElementById(currentActionName);
 if(currentActionElement)currentActionElement.onclick=()=>window.mapReviewCameraControls(currentActionName);
}

// 표준 UI는 상태만 전달하고 모든 렌더링·시점 갱신은 브라우저에서 수행한다.
window.mapReviewSelectMap=selectReviewMap;
window.mapReviewFocusBuilding=focusReviewBuilding;
window.mapReviewDisplayOptions=(currentCharacterVisible,currentBoundaryVisible,currentEdgesVisible,currentShadowProfileName='contrast')=>{
 const currentOptionValues=[currentCharacterVisible,currentBoundaryVisible,currentEdgesVisible];
 if(currentOptionValues.some(currentOptionValue=>typeof currentOptionValue!=='boolean'))throw Error('맵 표시 옵션은 참/거짓 값이어야 합니다.');
 if(!['baseline','contrast','broad'].includes(currentShadowProfileName))throw Error('지원하지 않는 캐릭터 그림자 검수안입니다.');
 Object.assign(currentDisplayOptions,{'show-character':currentCharacterVisible,'show-safe-boundary':currentBoundaryVisible,edges:currentEdgesVisible,'shadow-profile':currentShadowProfileName});
 renderBlockMap();
};
window.mapReviewControlOptions=()=>({maps:availableMapRecords.map(currentMapEntry=>[currentMapEntry.name,currentMapEntry.id]),selected:selectedMapIdentifier,townSpecific:isTownSpecificReviewPage||isCharacterReviewPage,field:isFieldMapReview,characterReview:isCharacterReviewPage,buildings:currentMapRecord.buildings.map(currentBuildingEntry=>[currentBuildingEntry.name,currentBuildingEntry.id])});

// 원본 에셋은 유지하고 마을 바닥 렌더링만 비교한다.
window.mapReviewGroundPreview=(currentPreviewMode)=>{
 if(!isCharacterReviewPage)throw Error('캐릭터 표현 검수에서 사용하세요.');
 if(!Object.hasOwn(GROUND_CONTRAST_PREVIEW_VALUES,currentPreviewMode))throw Error('지원하지 않는 바닥 대비입니다.');
 currentGroundPreviewMode=currentPreviewMode;renderBlockMap();
 return currentPreviewMode==='original'?'원본 바닥 대비':'실험 · 바닥 대비 65% · 캐릭터와 건물은 원본 유지';
};

window.mapReviewOutlinePreview=(currentOutlineEnabled)=>{
 if(!isCharacterReviewPage)throw Error('캐릭터 표현 검수에서 사용하세요.');
 if(typeof currentOutlineEnabled!=='boolean')throw Error('외곽선 옵션은 참/거짓이어야 합니다.');
 currentOutlinePreviewEnabled=currentOutlineEnabled;renderBlockMap();
 return currentOutlineEnabled?'실험 · 캐릭터 1px 짙은 외곽선':'캐릭터 원본';
};

window.mapReviewRimPreview=(currentRimEnabled)=>{
 if(!isCharacterReviewPage)throw Error('캐릭터 표현 검수에서 사용하세요.');
 if(typeof currentRimEnabled!=='boolean')throw Error('윤곽광 옵션은 참/거짓이어야 합니다.');
 currentRimPreviewEnabled=currentRimEnabled;renderBlockMap();
 return currentRimEnabled?'실험 · 얇은 밝은 윤곽광 적용':'밝은 윤곽광 해제';
};

window.characterReviewGroundTile=(currentTextureIdentifier)=>{
 if(!isCharacterReviewPage)throw Error('캐릭터 표현 검수에서 사용하세요.');
 if(!CHARACTER_REVIEW_TILE_NAMES.includes(currentTextureIdentifier)||!loadedTextureImages[currentTextureIdentifier])throw Error('지원하지 않는 검수 바닥입니다.');
 groundTextureNames.paving=currentTextureIdentifier;
 renderAppliedTileSourceList();
 renderBlockMap();
 return '양쪽 검수 맵에 동일한 바닥을 적용했습니다.';
};

window.characterReviewContactShadow=(currentShadowEnabled)=>{
 if(!isCharacterReviewPage||typeof currentShadowEnabled!=='boolean')throw Error('캐릭터 검수 그림자 설정 오류');
 currentShadowPreviewEnabled=currentShadowEnabled;renderBlockMap();return '조정본의 접지 그림자를 변경했습니다.';
};

// GUI와 헤드리스 CLI 캡처가 같은 설정·렌더 함수를 사용한다.
window.characterReviewCaptureSettings=()=>({ground:groundTextureNames.paving,zoom:2,column:currentCharacterCell.column,row:currentCharacterCell.row,rotation:currentCameraRotation,outline:currentOutlinePreviewEnabled,outline_width:currentOutlineBaseWidth,rim:currentRimPreviewEnabled,shadow:currentShadowPreviewEnabled,shadow_profile:currentDisplayOptions['shadow-profile'],contrast:currentGroundPreviewMode,width:768,height:576});
if(currentMapCanvas.dataset.capture==='true'){
 const currentCaptureSettings=await fetchMapReviewRecord('capture-settings.json');
 currentMapCanvas.style.width=currentCaptureSettings.width+'px';currentMapCanvas.style.height=currentCaptureSettings.height+'px';
 groundTextureNames.paving=currentCaptureSettings.ground;
 currentCharacterCell={column:currentCaptureSettings.column,row:currentCaptureSettings.row};
 currentCameraRotation=currentCaptureSettings.rotation;
 currentOutlineBaseWidth=currentCaptureSettings.outline_width;currentOutlinePreviewEnabled=currentCaptureSettings.outline;currentRimPreviewEnabled=currentCaptureSettings.rim;
 currentShadowPreviewEnabled=currentCaptureSettings.shadow;currentDisplayOptions['shadow-profile']=currentCaptureSettings.shadow_profile;
 currentGroundPreviewMode=currentCaptureSettings.contrast;
 centerCharacterView();changeMapZoom(currentCaptureSettings.zoom/currentScaleValue);
 const currentCaptureResponse=await fetch('/capture-result',{method:'POST',headers:{'Content-Type':'application/json','X-Capture-Token':currentCaptureSettings.token},body:JSON.stringify({baseline:document.querySelector('#character-baseline-map').toDataURL('image/png'),adjusted:currentMapCanvas.toDataURL('image/png')})});
 if(!currentCaptureResponse.ok)throw Error('렌더 캡처 저장 실패');
}
