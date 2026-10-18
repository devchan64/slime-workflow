import {installSourceSizePreview} from './source-size-preview.js';
import {resolveCityTileTextures,selectFieldRoadFrame,resolveFieldTerrainFrame,collectTerrainTextureSources,collectMapTextureSources,collectMapResourceKeys,loadMapResourceImages} from './vendor/field-renderer/__FIELD_RENDERER_VERSION__/town-renderer.mjs';
import {CHARACTER_OUTLINE_BASE_WIDTH,CHARACTER_OUTLINE_BASE_COLOR,CHARACTER_SEPARATOR_BASE_WIDTH,CHARACTER_SEPARATOR_BASE_COLOR,CHARACTER_CONTACT_SHADOW_COLOR as GAME_CONTACT_SHADOW_COLOR,CHARACTER_CONTACT_SHADOW_ALPHA_SCALE,ACTOR_CONTACT_SHADOW_CONTRACT} from './vendor/field-renderer/__FIELD_RENDERER_VERSION__/game-render-profile.mjs';
import {createFieldReviewFrame,pickFieldReviewCell} from './field-map-renderer.js';
import {FIELD_RENDER_METRICS,projectSurfaceCell} from './vendor/field-renderer/__FIELD_RENDERER_VERSION__/field-renderer.mjs';
import {resolveFieldActorContactShadow} from './vendor/field-renderer/__FIELD_RENDERER_VERSION__/field-renderer.mjs';
const MAP_FIT_HORIZONTAL_PADDING=160,MAP_FIT_VERTICAL_PADDING=80,MAP_FIT_BOTTOM_MARGIN=40,FIELD_FIT_TOP_MARGIN=160;
const MIN_MAP_SCALE=0.05,MAX_MAP_SCALE=4,MAP_ZOOM_FACTOR=1.25,MAP_DRAG_THRESHOLD=4,MAP_KEYBOARD_PAN_DISTANCE=48;
const CHARACTER_CELL_KEY_OFFSETS={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]};
let activeMapPointer=null,suppressMarkerClick=false;
const currentMapCanvas=document.querySelector('#map');
async function fetchMapReviewRecord(currentFilePath){
 const currentRequestUrl=new URL(currentFilePath,import.meta.url);
 let currentFetchResponse;
 try{currentFetchResponse=await fetch(currentRequestUrl,{cache:'no-store'});}
 catch(currentNetworkError){throw Error(`맵 서버 연결 실패: ${currentRequestUrl.pathname}. 서버 실행 상태를 확인한 뒤 검수 화면을 새로고침하세요.`,{cause:currentNetworkError});}
 if(!currentFetchResponse.ok){
  const currentResponseType=currentFetchResponse.headers.get('content-type')??'';
  const currentFailureDetail=currentResponseType.includes('application/json')?(await currentFetchResponse.json()).error:'';
  throw Error(`맵 데이터 로드 실패 (${currentFetchResponse.status}): ${currentRequestUrl.pathname}${currentFailureDetail?' · '+currentFailureDetail:''}`);
 }
 return currentFetchResponse.json();
}
const gameRenderMetrics=await fetchMapReviewRecord('game-render-metrics.json');
const blockRenderProfile=await fetchMapReviewRecord('block-render-profile.json');
const TOWN_BLOCK_HEIGHT=blockRenderProfile.blockHeight;
const BLOCK_BOUNDARY_COLOR='#dce5ef';
if(!Number.isInteger(TOWN_BLOCK_HEIGHT)||TOWN_BLOCK_HEIGHT<=0)throw Error('마을 블록 높이 설정이 올바르지 않습니다.');
const townHalfTileWidth=gameRenderMetrics.townTileWidth/2,townHalfTileHeight=gameRenderMetrics.townTileHeight/2;
const currentMapCatalog=await fetchMapReviewRecord('block-map-index.json');
const currentRequestedKind=new URLSearchParams(location.search).get('mapKind')||currentMapCatalog.find(currentMapEntry=>currentMapEntry.id===new URLSearchParams(location.search).get('map'))?.kind;
const availableMapRecords=currentRequestedKind?currentMapCatalog.filter(currentMapEntry=>currentMapEntry.kind===currentRequestedKind):currentMapCatalog;
const isCharacterReviewPage=currentMapCanvas.dataset.characterReview==='true';
const CHARACTER_REVIEW_RESOLUTION_SCALE=isCharacterReviewPage?2:1;
const CHARACTER_REVIEW_GRID_SIZE=3;
const CHARACTER_REVIEW_TILE_NAMES=['paving','grass','meadow-road'];
const selectedMapIdentifier=new URLSearchParams(location.search).get('map')||availableMapRecords[0].id;
const isTownSpecificReviewPage=false;
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
const GROUND_REDUCED_SATURATION=0.7;
let currentGroundSaturationReduced=false;
const GROUND_REDUCED_BRIGHTNESS=0.7;
let currentGroundBrightnessReduced=false;
let currentOutlinePreviewEnabled=true;
let currentRimPreviewEnabled=true;
let currentShadowPreviewEnabled=true;
let currentCharacterRimCanvas=null;
const CHARACTER_RIM_PREVIEW_COLOR='#'+CHARACTER_SEPARATOR_BASE_COLOR.toString(16).padStart(6,'0');
const CHARACTER_RIM_BAND_WIDTH=CHARACTER_SEPARATOR_BASE_WIDTH;
let currentOutlineBaseWidth=CHARACTER_OUTLINE_BASE_WIDTH;
let currentCharacterSilhouetteCanvas=null;
const CHARACTER_OUTLINE_PREVIEW_COLOR='#'+CHARACTER_OUTLINE_BASE_COLOR.toString(16).padStart(6,'0');
const CHARACTER_CONTACT_SHADOW_COLOR='#'+GAME_CONTACT_SHADOW_COLOR.toString(16).padStart(6,'0');
const CHARACTER_CONTACT_SHADOW_SIZE_SCALE=1;
let currentShadowColorOverride=isCharacterReviewPage?CHARACTER_CONTACT_SHADOW_COLOR:null;
const CHARACTER_OUTLINE_PIXEL_OFFSETS=[[-1,0],[1,0],[0,-1],[0,1],[-0.707,-0.707],[0.707,-0.707],[-0.707,0.707],[0.707,0.707]];
const currentDisplayOptions={'show-character':true,'show-safe-boundary':true,edges:false,'tile-edges':false,'shadow-profile':ACTOR_CONTACT_SHADOW_CONTRACT.profile};
function readReviewOption(currentOptionName){return document.getElementById(currentOptionName)?.checked??currentDisplayOptions[currentOptionName];}
// 검수용 반복 견본은 게임 맵 원본과 분리하며 등록된 타일·캐릭터만 공유한다.
const currentMapRecord=isCharacterReviewPage?{
 id:'character-review',name:'캐릭터 표현',reviewLabel:'3×3 검수 맵',safeTown:true,
 columns:CHARACTER_REVIEW_GRID_SIZE,rows:CHARACTER_REVIEW_GRID_SIZE,
 terrainCodes:{p:'paving'},terrainRows:Array(CHARACTER_REVIEW_GRID_SIZE).fill('p'.repeat(CHARACTER_REVIEW_GRID_SIZE)),
 startPoint:{column:Math.floor(CHARACTER_REVIEW_GRID_SIZE/2),row:Math.floor(CHARACTER_REVIEW_GRID_SIZE/2)},blocked:[],buildings:[],
}:await fetchMapReviewRecord(selectedMapRecord.path);
const currentMapLoadController=new AbortController();
window.addEventListener('pagehide',()=>currentMapLoadController.abort(),{once:true});
const isFieldMapReview=currentMapRecord.safeTown===false;
const currentDrawingContext=isCharacterReviewPage?currentMapCanvas.getContext('2d'):null;
const currentSafeVisualRecords=isFieldMapReview?await fetchMapReviewRecord('field-safe-visuals.json'):{};
const currentSafeVisualImages=await loadMapResourceImages(Object.entries(currentSafeVisualRecords).map(([currentVisualName,currentVisualRecord])=>({key:currentVisualName,url:new URL(currentVisualRecord.image,import.meta.url).href})),{signal:currentMapLoadController.signal});
if(document.querySelector('#show-safe-boundary'))document.querySelector('#show-safe-boundary').closest('label').hidden=!isFieldMapReview;
const loadedGuardImages=await loadMapResourceImages((currentMapRecord.guardCenters??[]).map(currentGuardRecord=>({key:currentGuardRecord.path,url:new URL(currentGuardRecord.image,import.meta.url).href})),{signal:currentMapLoadController.signal});
let currentFieldFrame=null;
const currentReviewTitle=currentMapRecord.name+' · '+currentMapRecord.reviewLabel;
document.querySelector('#map-title').textContent=currentReviewTitle;
document.title=currentReviewTitle;
document.querySelector('.map-toolbar')?.setAttribute('aria-label',currentMapRecord.reviewLabel+' 도구');
currentMapCanvas.setAttribute('aria-label',currentReviewTitle+'. 방향키로 화면 이동, Shift+좌우로 캐릭터 열 이동, Shift+상하로 행 이동. 더하기와 빼기 키로 확대 또는 축소하며 0 키로 전체 보기를 적용합니다.');
const currentMaterialColors=await fetchMapReviewRecord('block-materials.json');
const currentTextureRecords=await fetchMapReviewRecord('/management/map-assets/textures');
const currentResourceKeys=isCharacterReviewPage?CHARACTER_REVIEW_TILE_NAMES:collectMapResourceKeys(currentMapRecord,isFieldMapReview?'field':'town');
const currentGameTextureSources=collectMapTextureSources();
const currentSelectedTextureRecords={};
const currentSelectedGameKeys={};
for(const currentResourceKey of currentResourceKeys){
 const currentSourcePath=currentGameTextureSources[currentResourceKey];
 const currentCatalogEntry=currentSourcePath?Object.entries(currentTextureRecords).find(([,currentTextureRecord])=>currentTextureRecord.source===currentSourcePath):Object.entries(currentTextureRecords).find(([currentTextureName])=>currentTextureName===currentResourceKey);
 if(!currentCatalogEntry)throw Error('선택 맵 리소스가 카탈로그에 없습니다: '+currentResourceKey);
 currentSelectedTextureRecords[currentCatalogEntry[0]]=currentCatalogEntry[1];currentSelectedGameKeys[currentResourceKey]=currentCatalogEntry[0];
}
const loadedTextureImages=await loadMapResourceImages(Object.entries(currentSelectedTextureRecords).map(([currentTextureKey,currentTextureRecord])=>({key:currentTextureKey,url:new URL(currentTextureRecord.path,import.meta.url).href})),{signal:currentMapLoadController.signal,onProgress:currentLoadProgress=>{document.querySelector('#status').textContent=`선택 맵 리소스 불러오는 중 · ${currentLoadProgress.completed} / ${currentLoadProgress.total}`;}});
const currentResourceSummary=document.createElement('p');currentResourceSummary.setAttribute('role','status');currentResourceSummary.textContent=`선택 맵 타일·오브젝트 ${Object.keys(currentSelectedTextureRecords).length}종 로드 · 전체 카탈로그 ${Object.keys(currentTextureRecords).length}종`;document.querySelector('#status').after(currentResourceSummary);
document.querySelector('#status').textContent='기본 캐릭터 원본 불러오는 중';
const reviewCharacterRecord=await fetchMapReviewRecord('review-character.json');
const {character:reviewCharacterImage}=await loadMapResourceImages([{key:'character',url:new URL(reviewCharacterRecord.image,import.meta.url).href}],{signal:currentMapLoadController.signal});
document.querySelector('#status').textContent='맵 렌더러 초기화 중';
const currentSharedFieldModule=!isCharacterReviewPage?await import('./field-map-view.js'):null;
const currentSharedFieldView=!isCharacterReviewPage?await currentSharedFieldModule.createSharedFieldReview(currentMapCanvas,loadedTextureImages,reviewCharacterImage,reviewCharacterRecord,loadedGuardImages,currentSafeVisualImages,currentTextureRecords,currentSelectedGameKeys,isFieldMapReview):null;
// 캐릭터 검수의 단일 바닥만 별도로 선택한다. 마을·필드는 공용 렌더러 원본을 사용한다.
const groundTextureNames={paving:'paving'};
// 로더의 공통 준비 타일과 실제 배치 타일을 구분한다.
const currentAppliedGroundKeys=new Set();
for(const [currentRowIndex,currentTerrainRow] of currentMapRecord.terrainRows.entries()){
 for(const [currentColumnIndex,currentTerrainCode] of [...currentTerrainRow].entries()){
  const currentTerrainName=currentMapRecord.terrainCodes[currentTerrainCode];
  const currentOverrideRecord=(currentMapRecord.groundOverrides??[]).find(currentGroundRecord=>currentGroundRecord.position.column===currentColumnIndex&&currentGroundRecord.position.row===currentRowIndex);
  if(currentOverrideRecord){currentAppliedGroundKeys.add(currentOverrideRecord.textureKey);continue;}
  currentAppliedGroundKeys.add(isCharacterReviewPage?'paving':isFieldMapReview?'terrain-source-'+resolveFieldTerrainFrame(currentTerrainName,currentMapRecord.id):resolveCityTileTextures(null,currentTerrainName,currentMapRecord.id,0).ground);
  if(isFieldMapReview&&currentTerrainName==='boulder')currentAppliedGroundKeys.add('terrain-source-grass');
 }
}
const currentAppliedGameKeys=Object.fromEntries(Object.entries(currentSelectedGameKeys).filter(([currentGameKey])=>!currentGameKey.startsWith('terrain-source-')||currentAppliedGroundKeys.has(currentGameKey)));
installSourceSizePreview(currentTextureRecords,currentAppliedGameKeys,currentMapRecord);
let currentAppliedSourceSignature=null;
function renderAppliedTileSourceList(){
 const currentAssetGroups={tiles:new Set(),buildings:new Set(),billboards:new Set()};
 const currentBuildingKeys=new Set((currentMapRecord.buildings??[]).map(currentBuildingRecord=>currentBuildingRecord.sprite?.textureKey));
 const currentBillboardKeys=new Set((currentMapRecord.objects??[]).map(currentObjectRecord=>currentObjectRecord.textureKey));
 for(const [currentGameKey,currentCatalogKey] of Object.entries(currentAppliedGameKeys)){
  const currentAssetSource=currentTextureRecords[currentCatalogKey].source;
  if(currentBuildingKeys.has(currentGameKey))currentAssetGroups.buildings.add(currentCatalogKey);
  else if(currentBillboardKeys.has(currentGameKey)||currentAssetSource.includes('/billboards/'))currentAssetGroups.billboards.add(currentCatalogKey);
  else if(currentAssetSource.includes('/tiles/'))currentAssetGroups.tiles.add(currentCatalogKey);
 }
 if(isCharacterReviewPage){
  for(const currentTerrainName of Object.values(currentMapRecord.terrainCodes)){
   const currentCatalogKey=groundTextureNames[currentTerrainName];
   if(currentCatalogKey)currentAssetGroups.tiles.add(currentCatalogKey);
  }
 }
 const currentNextSourceSignature=JSON.stringify([Object.fromEntries(Object.entries(currentAssetGroups).map(([currentGroupName,currentGroupKeys])=>[currentGroupName,[...currentGroupKeys].sort()])),currentSafeVisualRecords,currentMapRecord.guardCenters??[]]);
 if(currentAppliedSourceSignature===currentNextSourceSignature)return;
 const currentGroupSelectors={tiles:'#applied-tile-list',buildings:'#applied-building-list',billboards:'#applied-billboard-list'};
 for(const [currentGroupName,currentGroupKeys] of Object.entries(currentAssetGroups)){
  const currentSourceList=document.querySelector(currentGroupSelectors[currentGroupName]);
  if(!currentSourceList)throw Error('에셋 분류 영역이 없습니다. 검수 화면을 새로고침하세요.');
  currentSourceList.replaceChildren();
  const currentGroupSummary=document.createElement('p');
  currentGroupSummary.textContent=`${currentGroupKeys.size}종 · 원본 해상도 내림차순. 썸네일을 선택하면 원본 이미지를 엽니다. 표시된 해상도는 파일 크기이며 맵에서의 표시 크기와 다릅니다.`;
  currentSourceList.append(currentGroupSummary);
  if(!currentGroupKeys.size)continue;
  const currentSourceTable=document.createElement('table');
  const currentTableHeading=document.createElement('thead');
  const currentHeadingRow=document.createElement('tr');
  for(const currentHeadingLabel of ['미리보기','원본 이름','해상도']){
   const currentHeadingCell=document.createElement('th');currentHeadingCell.scope='col';currentHeadingCell.textContent=currentHeadingLabel;currentHeadingRow.append(currentHeadingCell);
  }
  currentTableHeading.append(currentHeadingRow);currentSourceTable.append(currentTableHeading);
  const currentTableBody=document.createElement('tbody');
  for(const currentCatalogKey of [...currentGroupKeys].sort((firstCatalogKey,secondCatalogKey)=>{
   const firstSourceSize=currentTextureRecords[firstCatalogKey].source_size??[0,0],secondSourceSize=currentTextureRecords[secondCatalogKey].source_size??[0,0];
   return Math.max(...secondSourceSize)-Math.max(...firstSourceSize)||firstCatalogKey.localeCompare(secondCatalogKey);
  })){
   const currentAssetRecord=currentTextureRecords[currentCatalogKey];
   const currentSourceItem=document.createElement('tr');
   const currentPreviewCell=document.createElement('td');
   const currentAssetLink=document.createElement('a');
   currentAssetLink.href=new URL(currentAssetRecord.path,import.meta.url).href;currentAssetLink.target='_blank';currentAssetLink.rel='noopener';currentAssetLink.setAttribute('aria-label',`${currentCatalogKey} 원본 이미지 열기`);
   const currentAssetThumbnail=document.createElement('img');
   const currentSourceDimensions=currentAssetRecord.source_size??[1,1];
   const currentThumbnailScale=96/Math.max(...currentSourceDimensions);
   currentAssetThumbnail.width=Math.round(currentSourceDimensions[0]*currentThumbnailScale);currentAssetThumbnail.height=Math.round(currentSourceDimensions[1]*currentThumbnailScale);
   currentAssetThumbnail.src=currentAssetLink.href;currentAssetThumbnail.alt=`${currentCatalogKey} 원본 썸네일`;currentAssetThumbnail.loading='lazy';
   currentAssetLink.append(currentAssetThumbnail);currentPreviewCell.append(currentAssetLink);
   const currentNameCell=document.createElement('td');currentNameCell.textContent=currentCatalogKey;currentNameCell.title=currentAssetRecord.source;
   const currentCopyButton=document.createElement('button');currentCopyButton.type='button';currentCopyButton.textContent='이름 복사';currentCopyButton.setAttribute('aria-label',`${currentCatalogKey} 이름 복사`);
   const currentCopyStatus=document.createElement('span');currentCopyStatus.setAttribute('role','status');
   currentCopyButton.addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(currentCatalogKey);currentCopyStatus.textContent=' 복사 완료';}
    catch(currentClipboardError){currentCopyStatus.textContent=' 복사 실패 · 브라우저 클립보드 권한을 확인하세요.';}
   });
   currentNameCell.append(document.createElement('br'),currentCopyButton,currentCopyStatus);
   const currentSizeCell=document.createElement('td');currentSizeCell.textContent=`${currentAssetRecord.source_size?.join(' × ')||'?'} px`;
   if(currentGroupName==='tiles'&&currentAssetRecord.normalization_warning){const currentWarningLabel=document.createElement('p');currentWarningLabel.textContent=currentAssetRecord.normalization_warning;currentNameCell.append(currentWarningLabel);}
   currentSourceItem.append(currentPreviewCell,currentNameCell,currentSizeCell);currentTableBody.append(currentSourceItem);
  }
  currentSourceTable.append(currentTableBody);currentSourceList.append(currentSourceTable);
 }
 const currentStructureList=document.querySelector('#applied-structure-list');currentStructureList.replaceChildren();
 for(const [currentVisualName,currentVisualRecord] of Object.entries(currentSafeVisualRecords)){
  const currentVisualItem=document.createElement('li'),currentVisualThumbnail=document.createElement('img'),currentVisualLabel=document.createElement('span');
  currentVisualThumbnail.width=42;currentVisualThumbnail.height=42;currentVisualThumbnail.src=new URL(currentVisualRecord.image,import.meta.url).href;currentVisualThumbnail.alt=currentVisualName==='tower'?'결계탑 원본':'결계 오러 원본';
  currentVisualLabel.textContent=currentVisualThumbnail.alt+' · '+currentVisualRecord.sourceSize.join('×');
  currentVisualItem.title=`${currentVisualRecord.provenance.managementId} · ${currentVisualRecord.provenance.version} · SHA-256 ${currentVisualRecord.provenance.sha256}`;
  currentVisualItem.append(currentVisualThumbnail,currentVisualLabel);currentStructureList.append(currentVisualItem);
 }
 for(const currentGuardRecord of currentMapRecord.guardCenters??[]){
  const currentSourceItem=document.createElement('li'),currentAssetThumbnail=document.createElement('img'),currentAssetLabel=document.createElement('span');
  currentAssetThumbnail.width=42;currentAssetThumbnail.height=42;currentAssetThumbnail.src=currentGuardRecord.image;currentAssetThumbnail.alt='경비센터 원본';currentAssetThumbnail.loading='lazy';
  currentAssetLabel.textContent=`경비센터 · ${currentGuardRecord.cityId} · ${currentGuardRecord.provenance.version}`;
  currentSourceItem.title=`${currentGuardRecord.provenance.managementId} · SHA-256 ${currentGuardRecord.provenance.sha256}`;
  currentSourceItem.append(currentAssetThumbnail,currentAssetLabel);currentStructureList.append(currentSourceItem);
 }
 if(!currentStructureList.childElementCount){const currentEmptyItem=document.createElement('li');currentEmptyItem.textContent='적용된 원본 없음';currentStructureList.append(currentEmptyItem);}
 currentAppliedSourceSignature=currentNextSourceSignature;
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
function projectBlockVertex(currentVertexPoint){let currentColumnValue=currentVertexPoint.column,currentRowValue=currentVertexPoint.row;for(let currentRotationIndex=0;currentRotationIndex<currentCameraRotation;currentRotationIndex++)[currentColumnValue,currentRowValue]=[-currentRowValue,currentColumnValue];return {x:(currentColumnValue-currentRowValue)*townHalfTileWidth,y:(currentColumnValue+currentRowValue)*townHalfTileHeight-(currentVertexPoint.height??0)-(currentMapRecord.elevations?.[Math.max(0,Math.min(currentMapRecord.rows-1,Math.floor(currentVertexPoint.row)))]?.[Math.max(0,Math.min(currentMapRecord.columns-1,Math.floor(currentVertexPoint.column)))]??0)*FIELD_RENDER_METRICS.elevationHeight}}
function drawSurfacePolygon(currentSurfacePoints,currentFillColor){currentDrawingContext.beginPath();currentSurfacePoints.forEach((currentPointValue,currentPointIndex)=>currentPointIndex?currentDrawingContext.lineTo(currentPointValue.x,currentPointValue.y):currentDrawingContext.moveTo(currentPointValue.x,currentPointValue.y));currentDrawingContext.closePath();currentDrawingContext.fillStyle=currentFillColor;currentDrawingContext.fill();if(readReviewOption('edges')){currentDrawingContext.strokeStyle=BLOCK_BOUNDARY_COLOR;currentDrawingContext.lineWidth=1/currentScaleValue;currentDrawingContext.stroke()}}
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
 const currentSavedOutlineWidth=currentOutlineBaseWidth;
 const currentComparisonCanvas=document.querySelector('#character-baseline-map');
 try{
  currentOutlinePreviewEnabled=true;currentRimPreviewEnabled=true;currentOutlineBaseWidth=CHARACTER_OUTLINE_BASE_WIDTH;currentShadowPreviewEnabled=true;currentShadowColorOverride=CHARACTER_CONTACT_SHADOW_COLOR;currentDisplayOptions['shadow-profile']=ACTOR_CONTACT_SHADOW_CONTRACT.profile;
  drawCurrentMapScene(currentFitRequested);
  currentComparisonCanvas.width=currentMapCanvas.width;currentComparisonCanvas.height=currentMapCanvas.height;
  currentComparisonCanvas.getContext('2d').drawImage(currentMapCanvas,0,0);
 }finally{
  currentOutlinePreviewEnabled=currentSavedOutline;currentRimPreviewEnabled=currentSavedRim;currentOutlineBaseWidth=currentSavedOutlineWidth;
  currentDisplayOptions['shadow-profile']=currentSavedShadow;currentShadowPreviewEnabled=currentSavedShadowEnabled;currentShadowColorOverride=currentSavedShadowColor;
 }
 drawCurrentMapScene(false);
 document.querySelector('#status').textContent=`3×3 검수 맵 · 캐릭터 (${currentCharacterCell.column+1}, ${currentCharacterCell.row+1}) · 사람 높이 ${gameRenderMetrics.characterHeight}px · 양쪽 동일 위치·크기 · 원본은 게임 공용 렌더링 상수 적용`;
}
function drawCurrentMapScene(currentFitRequested=false){
 if(!isCharacterReviewPage){renderSharedReviewMap(currentFitRequested);return;}
currentMapCanvas.width=currentMapCanvas.clientWidth*CHARACTER_REVIEW_RESOLUTION_SCALE;currentMapCanvas.height=currentMapCanvas.clientHeight*CHARACTER_REVIEW_RESOLUTION_SCALE;const currentAllCorners=isFieldMapReview?currentFieldFrame.points:[{column:0,row:0},{column:currentMapRecord.columns,row:0},{column:0,row:currentMapRecord.rows},{column:currentMapRecord.columns,row:currentMapRecord.rows}].map(projectBlockVertex);if(currentFitRequested){const currentMinX=Math.min(...currentAllCorners.map(p=>p.x)),currentMaxX=Math.max(...currentAllCorners.map(p=>p.x)),currentMinY=Math.min(...currentAllCorners.map(p=>p.y))-TOWN_BLOCK_HEIGHT*2,currentMaxY=Math.max(...currentAllCorners.map(p=>p.y))+40;currentScaleValue=Math.min(currentMapCanvas.clientWidth/(currentMaxX-currentMinX+160),currentMapCanvas.clientHeight/(currentMaxY-currentMinY+80));currentOffsetX=currentMapCanvas.clientWidth/2-(currentMinX+currentMaxX)/2*currentScaleValue;currentOffsetY=currentMapCanvas.clientHeight/2-(currentMinY+currentMaxY)/2*currentScaleValue}
updateReviewZoomControls();
currentDrawingContext.setTransform(currentScaleValue*CHARACTER_REVIEW_RESOLUTION_SCALE,0,0,currentScaleValue*CHARACTER_REVIEW_RESOLUTION_SCALE,currentOffsetX*CHARACTER_REVIEW_RESOLUTION_SCALE,currentOffsetY*CHARACTER_REVIEW_RESOLUTION_SCALE);
currentDrawingContext.filter=`contrast(${GROUND_CONTRAST_PREVIEW_VALUES[currentGroundPreviewMode]}) saturate(${currentGroundSaturationReduced?GROUND_REDUCED_SATURATION:1}) brightness(${currentGroundBrightnessReduced?GROUND_REDUCED_BRIGHTNESS:1})`;
for(let currentRowIndex=0;currentRowIndex<currentMapRecord.rows;currentRowIndex++)for(let currentColumnIndex=0;currentColumnIndex<currentMapRecord.columns;currentColumnIndex++){const currentTerrainName=currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentRowIndex][currentColumnIndex]];drawSurfacePolygon([[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]].map(([c,r])=>projectBlockVertex({column:currentColumnIndex+c,row:currentRowIndex+r})),currentMaterialColors[currentTerrainName]);const currentGroundImage=loadedTextureImages[groundTextureNames[currentTerrainName]];if(currentGroundImage){const currentGroundVertices=[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]].map(([currentColumnOffset,currentRowOffset])=>({column:currentColumnIndex+currentColumnOffset,row:currentRowIndex+currentRowOffset,height:0}));drawTexturedSurface({top:true,ground:true,vertices:currentGroundVertices,points:currentGroundVertices.map(projectBlockVertex)},currentGroundImage)}}
currentDrawingContext.filter='none';
if(!isFieldMapReview)drawReviewCharacter(projectReviewCharacter()); currentDrawingContext.setTransform(1,0,0,1,0,0);const currentBuildingFloorSummary=[...new Set(currentMapRecord.buildings.map(currentBuildingRecord=>currentBuildingRecord.floors))].sort((firstFloorCount,secondFloorCount)=>firstFloorCount-secondFloorCount).map(currentFloorCount=>`${currentFloorCount}층 ${currentMapRecord.buildings.filter(currentBuildingRecord=>currentBuildingRecord.floors===currentFloorCount).length}개`).join(' · '),currentRoofHeightValues=[...new Set(currentMapRecord.buildings.flatMap(currentBuildingRecord=>currentBuildingRecord.blocks).filter(currentBlockRecord=>currentBlockRecord.material==='roof').map(currentBlockRecord=>currentBlockRecord.height))].sort((firstHeightValue,secondHeightValue)=>firstHeightValue-secondHeightValue),currentRoofHeightSummary=currentRoofHeightValues.join('·');document.querySelector('#status').textContent=isFieldMapReview?`필드 고도 ${Math.min(...currentMapRecord.elevations.flat())}–${Math.max(...currentMapRecord.elevations.flat())} · 높이 단위 ${FIELD_RENDER_METRICS.elevationHeight}px · 타일 ${FIELD_RENDER_METRICS.tileWidth}×${FIELD_RENDER_METRICS.tileHeight} · 계단 ${currentMapRecord.elevationTiles.length}개 · 고정 시점`:`고정 시점 · 건물 ${currentMapRecord.buildings.length}개 (${currentBuildingFloorSummary}) · 블록 ${currentMapRecord.buildings.reduce((s,b)=>s+b.blocks.length,0)}개 · 일반 블록 ${TOWN_BLOCK_HEIGHT}px · 지붕 경사 ${currentRoofHeightSummary}px · 사람 높이 ${gameRenderMetrics.characterHeight} · 마을 타일 ${gameRenderMetrics.townTileWidth}×${gameRenderMetrics.townTileHeight} · 지붕 보행 불가`}
function fitReviewMapCamera(currentCornerPoints,currentTopMargin){
 const currentMinimumX=Math.min(...currentCornerPoints.map(currentPointValue=>currentPointValue.x)),currentMaximumX=Math.max(...currentCornerPoints.map(currentPointValue=>currentPointValue.x));
 const currentMinimumY=Math.min(...currentCornerPoints.map(currentPointValue=>currentPointValue.y))-currentTopMargin,currentMaximumY=Math.max(...currentCornerPoints.map(currentPointValue=>currentPointValue.y))+MAP_FIT_BOTTOM_MARGIN;
 currentScaleValue=Math.min(currentMapCanvas.clientWidth/(currentMaximumX-currentMinimumX+MAP_FIT_HORIZONTAL_PADDING),currentMapCanvas.clientHeight/(currentMaximumY-currentMinimumY+MAP_FIT_VERTICAL_PADDING));
 currentOffsetX=currentMapCanvas.clientWidth/2-(currentMinimumX+currentMaximumX)/2*currentScaleValue;
 currentOffsetY=currentMapCanvas.clientHeight/2-(currentMinimumY+currentMaximumY)/2*currentScaleValue;
}
function updateReviewZoomControls(){
 document.querySelector('#zoom-level').textContent=Math.round(currentScaleValue*100)+'%';
 if(document.querySelector('#zoom-in'))document.querySelector('#zoom-in').disabled=currentScaleValue>=MAX_MAP_SCALE;
 if(document.querySelector('#zoom-out'))document.querySelector('#zoom-out').disabled=currentScaleValue<=MIN_MAP_SCALE;
}
function renderSharedReviewMap(currentFitRequested){
 if(isFieldMapReview&&(!currentFieldFrame||currentFieldFrame.options.rotation!==currentCameraRotation))currentFieldFrame=createFieldReviewFrame(currentMapRecord,currentCameraRotation);
 if(currentFitRequested){
  const currentCornerPoints=isFieldMapReview?currentFieldFrame.points:[{column:0,row:0},{column:currentMapRecord.columns,row:0},{column:0,row:currentMapRecord.rows},{column:currentMapRecord.columns,row:currentMapRecord.rows}].map(projectBlockVertex);
  fitReviewMapCamera(currentCornerPoints,isFieldMapReview?FIELD_FIT_TOP_MARGIN:TOWN_BLOCK_HEIGHT*2);
 }
 const currentRenderOptions={edges:readReviewOption('edges'),tileEdges:readReviewOption('tile-edges'),scale:currentScaleValue,offsetX:currentOffsetX,offsetY:currentOffsetY,character:readReviewOption('show-character'),characterCell:currentCharacterCell};
 if(isFieldMapReview){
  currentSharedFieldView.render(currentFieldFrame,currentMapRecord,{...currentRenderOptions,safe:readReviewOption('show-safe-boundary'),shadowProfile:currentDisplayOptions['shadow-profile']});
 }else{
  currentSharedFieldView.renderTown(currentMapRecord,{...currentRenderOptions,rotation:currentCameraRotation},projectBlockVertex);
  renderAppliedTileSourceList();
 }
 updateReviewZoomControls();
 document.querySelector('#status').textContent=isFieldMapReview
  ?`게임 공용 필드 렌더러 · 내부 해상도 2배 · 높이 단위 ${FIELD_RENDER_METRICS.elevationHeight}px · 타일 ${FIELD_RENDER_METRICS.tileWidth}×${FIELD_RENDER_METRICS.tileHeight} · 결계 높이 15px · 고정 시점`
  :`게임 공용 마을 렌더러 · 내부 해상도 2배 · 건물 ${currentMapRecord.buildings.length}개 · 고정 시점`;
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
if(document.querySelector('#edges'))document.querySelector('#edges').onchange=()=>renderBlockMap();
// 사이드바 애니메이션도 창 크기 변경 없이 표시 영역을 바꾼다.
let currentResizeFrameRequest=null;
let currentResizeObserverClosed=false;
const currentMapResizeObserver=new ResizeObserver(()=>{
 if(currentResizeObserverClosed||currentResizeFrameRequest!==null)return;
 currentResizeFrameRequest=requestAnimationFrame(()=>{
  currentResizeFrameRequest=null;
  const currentViewportBounds=currentMapCanvas.parentElement.getBoundingClientRect();
  // 숨겨진 영역은 다시 표시될 때 관찰 이벤트로 렌더링한다.
  if(currentViewportBounds.width<=0||currentViewportBounds.height<=0)return;
  try{renderBlockMap();}catch(currentResizeError){document.querySelector('#status').textContent='맵 크기 변경 실패: '+currentResizeError.message;}
 });
});
currentMapResizeObserver.observe(currentMapCanvas.parentElement);
window.addEventListener('pagehide',()=>{
 currentResizeObserverClosed=true;
 currentMapResizeObserver.disconnect();
 if(currentResizeFrameRequest!==null)cancelAnimationFrame(currentResizeFrameRequest);
 currentResizeFrameRequest=null;
},{once:true});
function placeReviewCharacterCell(currentColumnValue,currentRowValue){
 if(!Number.isInteger(currentColumnValue)||!Number.isInteger(currentRowValue)||currentColumnValue<0||currentColumnValue>=currentMapRecord.columns||currentRowValue<0||currentRowValue>=currentMapRecord.rows||currentBlockedCells.has(`${currentColumnValue},${currentRowValue}`)){
  document.querySelector('#status').textContent='이동할 수 없는 위치입니다. 맵 안의 이동 가능한 타일을 선택하세요.';
  return false;
 }
 currentCharacterCell={column:currentColumnValue,row:currentRowValue};renderBlockMap();
 if(!isCharacterReviewPage)document.querySelector('#status').textContent+=` · 캐릭터 (${currentColumnValue+1}, ${currentRowValue+1})`;
 return true;
}
currentMapCanvas.onclick=currentEvent=>{if(suppressMarkerClick){suppressMarkerClick=false;return;}const currentBounds=currentMapCanvas.getBoundingClientRect(),currentWorldX=(currentEvent.clientX-currentBounds.left-currentOffsetX)/currentScaleValue,currentWorldY=(currentEvent.clientY-currentBounds.top-currentOffsetY)/currentScaleValue;if(isFieldMapReview){const currentPickedCell=pickFieldReviewCell({x:currentWorldX,y:currentWorldY},currentFieldFrame);if(currentPickedCell)placeReviewCharacterCell(currentPickedCell.column,currentPickedCell.row);return;}let currentColumnValue=(currentWorldX/townHalfTileWidth+currentWorldY/townHalfTileHeight)/2,currentRowValue=(currentWorldY/townHalfTileHeight-currentWorldX/townHalfTileWidth)/2;for(let i=0;i<currentCameraRotation;i++)[currentColumnValue,currentRowValue]=[currentRowValue,-currentColumnValue];currentColumnValue=Math.round(currentColumnValue);currentRowValue=Math.round(currentRowValue);placeReviewCharacterCell(currentColumnValue,currentRowValue)};centerCharacterView();

// 포인터 아래의 지형 좌표를 유지하면서 배율을 변경한다.
function changeMapZoom(currentZoomFactor,currentAnchorX=currentMapCanvas.clientWidth/2,currentAnchorY=currentMapCanvas.clientHeight/2){
 const nextScaleValue=Math.max(MIN_MAP_SCALE,Math.min(MAX_MAP_SCALE,currentScaleValue*currentZoomFactor));
 currentOffsetX=currentAnchorX-(currentAnchorX-currentOffsetX)*nextScaleValue/currentScaleValue;
 currentOffsetY=currentAnchorY-(currentAnchorY-currentOffsetY)*nextScaleValue/currentScaleValue;
 currentScaleValue=nextScaleValue;renderBlockMap();
}

currentMapCanvas.onkeydown=currentKeyboardEvent=>{
 const currentCharacterOffset=CHARACTER_CELL_KEY_OFFSETS[currentKeyboardEvent.key];
 if(currentKeyboardEvent.shiftKey&&currentCharacterOffset){currentKeyboardEvent.preventDefault();placeReviewCharacterCell(currentCharacterCell.column+currentCharacterOffset[0],currentCharacterCell.row+currentCharacterOffset[1]);return;}

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
 'fit':()=>renderBlockMap(true),
 'zoom-in':()=>changeMapZoom(MAP_ZOOM_FACTOR),
 'zoom-out':()=>changeMapZoom(1/MAP_ZOOM_FACTOR),
 'actual-size':()=>{centerCharacterView();changeMapZoom(1/currentScaleValue);},
};
window.mapReviewCameraControls=(currentActionName)=>{
 if(!Object.hasOwn(currentCameraActions,currentActionName))throw Error('지원하지 않는 맵 시점 명령입니다.');
 currentCameraActions[currentActionName]();
 return `고정 시점 · 확대 ${Math.round(currentScaleValue*100)}%`;
};
for(const currentActionName of Object.keys(currentCameraActions)){
 const currentActionElement=document.getElementById(currentActionName);
 if(currentActionElement)currentActionElement.onclick=()=>window.mapReviewCameraControls(currentActionName);
}

// 표준 UI는 상태만 전달하고 모든 렌더링·시점 갱신은 브라우저에서 수행한다.
window.mapReviewSelectMap=selectReviewMap;
window.mapReviewFocusBuilding=focusReviewBuilding;
window.mapReviewDisplayOptions=(currentCharacterVisible,currentBoundaryVisible,currentEdgesVisible,currentShadowProfileName='contrast',currentTileEdgesVisible=false)=>{
 const currentOptionValues=[currentCharacterVisible,currentBoundaryVisible,currentEdgesVisible,currentTileEdgesVisible];
 if(currentOptionValues.some(currentOptionValue=>typeof currentOptionValue!=='boolean'))throw Error('맵 표시 옵션은 참/거짓 값이어야 합니다.');
 if(!['baseline','contrast','broad'].includes(currentShadowProfileName))throw Error('지원하지 않는 캐릭터 그림자 검수안입니다.');
 Object.assign(currentDisplayOptions,{'show-character':currentCharacterVisible,'show-safe-boundary':currentBoundaryVisible,edges:currentEdgesVisible,'tile-edges':currentTileEdgesVisible,'shadow-profile':currentShadowProfileName});
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
window.characterReviewGroundSaturation=(currentSaturationReduced)=>{
 if(!isCharacterReviewPage||typeof currentSaturationReduced!=='boolean')throw Error('바닥 채도 설정은 참/거짓이어야 합니다.');
 currentGroundSaturationReduced=currentSaturationReduced;renderBlockMap();return currentSaturationReduced?'바닥 채도 70% 적용':'바닥 원본 채도 적용';
};
window.characterReviewGroundBrightness=(currentBrightnessReduced)=>{
 if(!isCharacterReviewPage||typeof currentBrightnessReduced!=='boolean')throw Error('바닥 명도 설정은 참/거짓이어야 합니다.');
 currentGroundBrightnessReduced=currentBrightnessReduced;renderBlockMap();return currentBrightnessReduced?'바닥 명도 70% 적용':'바닥 원본 명도 적용';
};
window.characterReviewCaptureSettings=()=>({ground:groundTextureNames.paving,zoom:2,column:currentCharacterCell.column,row:currentCharacterCell.row,rotation:currentCameraRotation,outline:currentOutlinePreviewEnabled,outline_width:currentOutlineBaseWidth,rim:currentRimPreviewEnabled,shadow:currentShadowPreviewEnabled,shadow_profile:currentDisplayOptions['shadow-profile'],contrast:currentGroundPreviewMode,saturation_reduced:currentGroundSaturationReduced,brightness_reduced:currentGroundBrightnessReduced,width:768,height:576});
if(currentMapCanvas.dataset.capture==='true'){
 const currentCaptureSettings=await fetchMapReviewRecord('capture-settings.json');
 currentMapCanvas.style.width=currentCaptureSettings.width+'px';currentMapCanvas.style.height=currentCaptureSettings.height+'px';
 groundTextureNames.paving=currentCaptureSettings.ground;
 currentCharacterCell={column:currentCaptureSettings.column,row:currentCaptureSettings.row};
 currentCameraRotation=0;
 currentOutlineBaseWidth=currentCaptureSettings.outline_width;currentOutlinePreviewEnabled=currentCaptureSettings.outline;currentRimPreviewEnabled=currentCaptureSettings.rim;
 currentShadowPreviewEnabled=currentCaptureSettings.shadow;currentDisplayOptions['shadow-profile']=currentCaptureSettings.shadow_profile;
 currentGroundPreviewMode=currentCaptureSettings.contrast;
 currentGroundSaturationReduced=currentCaptureSettings.saturation_reduced;
 currentGroundBrightnessReduced=currentCaptureSettings.brightness_reduced;
 centerCharacterView();changeMapZoom(currentCaptureSettings.zoom/currentScaleValue);
 const currentCaptureResponse=await fetch('./capture-result',{method:'POST',headers:{'Content-Type':'application/json','X-Capture-Token':currentCaptureSettings.token},body:JSON.stringify({baseline:document.querySelector('#character-baseline-map').toDataURL('image/png'),adjusted:currentMapCanvas.toDataURL('image/png')})});
 if(!currentCaptureResponse.ok)throw Error('렌더 캡처 저장 실패');
}

window.mapReviewExportImage=async()=>{
 if(!currentSharedFieldView)throw Error('야외필드·도시맵에서 사용할 수 있습니다.');
 const currentGroundPoints=isFieldMapReview?currentFieldFrame.points:[{column:0,row:0},{column:currentMapRecord.columns,row:0},{column:0,row:currentMapRecord.rows},{column:currentMapRecord.columns,row:currentMapRecord.rows}].map(projectBlockVertex);
 const currentExportImage=await currentSharedFieldView.exportWholeMapImage(currentGroundPoints);
 const currentDownloadLink=document.getElementById('map-export-download');
 if(!currentDownloadLink)throw Error('다운로드 영역이 없습니다. 검수 화면을 새로고침하세요.');
 currentDownloadLink.href=currentExportImage.src;
 currentDownloadLink.download=`${currentMapRecord.id}-full-map-${new Date().toISOString().replace(/[:.]/g,'-')}.png`;
 currentDownloadLink.hidden=false;
 currentDownloadLink.textContent=`전체 맵 PNG 다운로드 (${currentExportImage.width}×${currentExportImage.height})`;
 currentDownloadLink.click();
 renderBlockMap();
 return `전체 맵 PNG 저장 · ${currentExportImage.width}×${currentExportImage.height}px · 현재 표시 옵션 적용`;
};
