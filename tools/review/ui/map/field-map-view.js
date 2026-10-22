import {resolveCityTileTextures,resolveTownGroundFrame,resolveReedFrameForMap,drawWaypoint,waypointMarkerScale,resolveFieldTileTextures,collectTerrainTextureSources,createTerrainAtlas,TERRAIN_ATLAS,drawCityBuildingSprite,resolveCityGroundDepth,TERRAIN_DEPTH,mapAnnotationDepth,resolveMapTileSize,resolveGrassFrameForMap,resolvePavingFrameForMap,selectFieldRoadFrame} from './vendor/field-renderer/__FIELD_RENDERER_VERSION__/town-renderer.mjs';
import {GAME_INTERNAL_RESOLUTION_SCALE,drawCharacterContactShadow,attachCharacterOutlineLayers,roadConnections,waterConnections} from './vendor/field-renderer/__FIELD_RENDERER_VERSION__/game-render-profile.mjs';
import * as Phaser from './vendor/field-renderer/__FIELD_RENDERER_VERSION__/phaser.mjs';
import {FIELD_TILE_BOUNDARY_ALPHA,FIELD_RENDER_METRICS,updateFieldActorOcclusion,resolveGuardDisplayPlacement,projectGuardDisplayCenter,GUARD_CENTER_FOOTPRINT_SIZE,drawTownMaterialEdges,drawFieldCellObjects,drawFieldSceneryObject,resolveFieldSceneryPlacement,resolveFieldSceneryDepth,resolveFieldSurfaceDepth,drawFieldAuraPanel,drawFieldMeshBoundary,buildFieldBoundaryPanels,rotateSurfacePosition} from './vendor/field-renderer/__FIELD_RENDERER_VERSION__/field-renderer.mjs';

const FIELD_REVIEW_ACTOR_DEPTH=TERRAIN_DEPTH.actor;
const MAP_HOVER_OVERLAY_COLOR=0x66ccff;
const MAP_HOVER_OVERLAY_ALPHA=0.22;
const MAP_HOVER_BORDER_WIDTH=2;
const MAP_HOVER_LABEL_STYLE={fontFamily:'sans-serif',fontSize:'14px',color:'#ffffff',backgroundColor:'#20252b',padding:{x:5,y:3}};
const MAP_HOVER_LABEL_OFFSET=8;
const MAP_HOVER_OVERLAY_DEPTH=1000000000;
const FIELD_REVIEW_TOWER_DEPTH=TERRAIN_DEPTH.overlay;
const FIELD_REVIEW_TERRAIN_CACHE=new WeakMap();

const TILE_BOUNDARY_LINE_COLOR=0xffe4a0;
function drawReviewTileBoundary(currentSceneObject,currentCenterPoint,currentTileWidth,currentTileHeight,currentSurfaceDepth){
 const currentBoundaryGraphic=currentSceneObject.add.graphics().setDepth(currentSurfaceDepth);
 currentBoundaryGraphic.lineStyle(1,TILE_BOUNDARY_LINE_COLOR,FIELD_TILE_BOUNDARY_ALPHA);
 currentBoundaryGraphic.beginPath();
 currentBoundaryGraphic.moveTo(currentCenterPoint.x,currentCenterPoint.y-currentTileHeight/2);
 currentBoundaryGraphic.lineTo(currentCenterPoint.x+currentTileWidth/2,currentCenterPoint.y);
 currentBoundaryGraphic.lineTo(currentCenterPoint.x,currentCenterPoint.y+currentTileHeight/2);
 currentBoundaryGraphic.lineTo(currentCenterPoint.x-currentTileWidth/2,currentCenterPoint.y);
 currentBoundaryGraphic.closePath();currentBoundaryGraphic.strokePath();
 return currentBoundaryGraphic;
}

const BLOCKED_REVIEW_OVERLAY_DEPTH=100000000;
const BLOCKED_REVIEW_AREA_COLOR=0xffffff;
const BLOCKED_REVIEW_HATCH_SPACING=20;
const BLOCKED_REVIEW_HATCH_WIDTH=2;
const BLOCKED_REVIEW_EDGE_WIDTH=5;
const BLOCKED_REVIEW_DASH_LENGTH=10;
const BLOCKED_REVIEW_DASH_GAP=6;
function drawReviewDashedBoundary(currentOverlayGraphic,currentFirstPoint,currentLastPoint){
 const currentDeltaX=currentLastPoint.x-currentFirstPoint.x,currentDeltaY=currentLastPoint.y-currentFirstPoint.y;
 const currentEdgeLength=Math.hypot(currentDeltaX,currentDeltaY);
 currentOverlayGraphic.lineStyle(BLOCKED_REVIEW_EDGE_WIDTH,BLOCKED_REVIEW_AREA_COLOR,1);
 for(let currentDashOffset=0;currentDashOffset<currentEdgeLength;currentDashOffset+=BLOCKED_REVIEW_DASH_LENGTH+BLOCKED_REVIEW_DASH_GAP){
  const currentEndOffset=Math.min(currentDashOffset+BLOCKED_REVIEW_DASH_LENGTH,currentEdgeLength);
  currentOverlayGraphic.beginPath();currentOverlayGraphic.moveTo(currentFirstPoint.x+currentDeltaX*currentDashOffset/currentEdgeLength,currentFirstPoint.y+currentDeltaY*currentDashOffset/currentEdgeLength);
  currentOverlayGraphic.lineTo(currentFirstPoint.x+currentDeltaX*currentEndOffset/currentEdgeLength,currentFirstPoint.y+currentDeltaY*currentEndOffset/currentEdgeLength);currentOverlayGraphic.strokePath();
 }
}
function drawReviewBlockedAreas(currentSceneObject,currentMapRecord,currentProjectCell,currentTileWidth,currentTileHeight){
 const currentBlockedPositions=new Map((currentMapRecord.blocked??[]).map(currentCellPosition=>[`${currentCellPosition.column},${currentCellPosition.row}`,currentCellPosition]));
 for(const currentObjectRecord of currentMapRecord.objects??[]){
  for(let currentColumnOffset=1;currentColumnOffset<(currentObjectRecord.groundFootprintColumns??1)-1;currentColumnOffset++)for(let currentRowOffset=1;currentRowOffset<(currentObjectRecord.groundFootprintRows??1)-1;currentRowOffset++){
   const currentCellPosition={column:currentObjectRecord.position.column+currentColumnOffset,row:currentObjectRecord.position.row+currentRowOffset};
   currentBlockedPositions.set(`${currentCellPosition.column},${currentCellPosition.row}`,currentCellPosition);
  }
 }
 const currentOverlayGraphic=currentSceneObject.add.graphics().setDepth(BLOCKED_REVIEW_OVERLAY_DEPTH);
 currentOverlayGraphic.lineStyle(BLOCKED_REVIEW_HATCH_WIDTH,BLOCKED_REVIEW_AREA_COLOR,1);
 for(const currentCellPosition of currentBlockedPositions.values()){
  const currentCenterPoint=currentProjectCell(currentCellPosition);
  if(!currentCenterPoint)continue;
  // 다이아몬드의 두 평행 변 사이에 선을 보간해 타일 밖으로 빗금이 새지 않게 한다.
  for(let currentHatchOffset=BLOCKED_REVIEW_HATCH_SPACING/2;currentHatchOffset<currentTileWidth;currentHatchOffset+=BLOCKED_REVIEW_HATCH_SPACING){
   const currentHatchRatio=currentHatchOffset/currentTileWidth;
   currentOverlayGraphic.beginPath();
   currentOverlayGraphic.moveTo(currentCenterPoint.x-currentTileWidth/2+currentHatchRatio*currentTileWidth/2,currentCenterPoint.y-currentHatchRatio*currentTileHeight/2);
   currentOverlayGraphic.lineTo(currentCenterPoint.x+currentHatchRatio*currentTileWidth/2,currentCenterPoint.y+currentTileHeight/2-currentHatchRatio*currentTileHeight/2);
   currentOverlayGraphic.strokePath();
  }
 }
 for(const currentObjectRecord of currentMapRecord.objects??[]){
  if(currentObjectRecord.groundFootprintColumns!==3||currentObjectRecord.groundFootprintRows!==2)continue;
  const currentFirstPoint=currentProjectCell({column:currentObjectRecord.position.column+1,row:currentObjectRecord.position.row});
  const currentSecondPoint=currentProjectCell({column:currentObjectRecord.position.column+1,row:currentObjectRecord.position.row+1});
  if(!currentFirstPoint||!currentSecondPoint)continue;
  const currentMiddlePoint={x:(currentFirstPoint.x+currentSecondPoint.x)/2,y:(currentFirstPoint.y+currentSecondPoint.y)/2};
  drawReviewDashedBoundary(currentOverlayGraphic,{x:currentMiddlePoint.x-currentTileWidth/4,y:currentMiddlePoint.y-currentTileHeight/4},{x:currentMiddlePoint.x+currentTileWidth/4,y:currentMiddlePoint.y+currentTileHeight/4});
 }
}

function readReviewConnectionMask(currentCellPosition,currentMapRecord,currentTerrainName,currentRotationValue){
 let currentTerrainCache=FIELD_REVIEW_TERRAIN_CACHE.get(currentMapRecord);
 if(!currentTerrainCache){currentTerrainCache=new Map();FIELD_REVIEW_TERRAIN_CACHE.set(currentMapRecord,currentTerrainCache);}
 let currentTerrainCells=currentTerrainCache.get(currentTerrainName);
 if(!currentTerrainCells){
 currentTerrainCells=new Set();
 for(let currentRowIndex=0;currentRowIndex<currentMapRecord.terrainRows.length;currentRowIndex++){
  const currentTerrainRow=currentMapRecord.terrainRows[currentRowIndex];
  for(let currentColumnIndex=0;currentColumnIndex<currentTerrainRow.length;currentColumnIndex++){
   if(currentMapRecord.terrainCodes[currentTerrainRow[currentColumnIndex]]===currentTerrainName)currentTerrainCells.add(currentColumnIndex+','+currentRowIndex);
  }
 }
 currentTerrainCache.set(currentTerrainName,currentTerrainCells);
 }
 let currentConnectionMask=(currentTerrainName==='road'?roadConnections:waterConnections)(currentCellPosition,currentMapRecord,currentTerrainCells);
 for(let currentTurnIndex=0;currentTurnIndex<currentRotationValue;currentTurnIndex++)currentConnectionMask=((currentConnectionMask<<1)&15)|(currentConnectionMask>>3);
 return currentConnectionMask;
}

export function resolveReviewTownFrame(currentMapRecord,currentTerrainName,currentCellPosition,currentConnectionMask){
 return currentTerrainName==='water'?`water-${currentConnectionMask}`:currentTerrainName==='road'?selectFieldRoadFrame(currentConnectionMask,currentCellPosition,true,currentMapRecord.id):currentTerrainName==='reed-bed'?resolveReedFrameForMap(currentMapRecord.id):currentTerrainName==='paving'?resolvePavingFrameForMap(currentMapRecord.id):currentTerrainName==='grass'?resolveGrassFrameForMap(currentMapRecord.id):resolveTownGroundFrame(currentMapRecord.id,currentTerrainName);
}

const MAP_EXPORT_MAXIMUM_EDGE=4096;
const MAP_EXPORT_WORLD_PADDING=80;
const MAP_EXPORT_TIMEOUT_MS=15000;

function readReviewViewportSize(currentMapCanvas){
 const currentViewportBounds=currentMapCanvas.parentElement.getBoundingClientRect();
 const currentPixelWidth=Math.round(currentViewportBounds.width*GAME_INTERNAL_RESOLUTION_SCALE);
 const currentPixelHeight=Math.round(currentViewportBounds.height*GAME_INTERNAL_RESOLUTION_SCALE);
 if(!Number.isFinite(currentPixelWidth)||!Number.isFinite(currentPixelHeight)||currentPixelWidth<=0||currentPixelHeight<=0)throw Error('맵 표시 영역 크기가 유효하지 않습니다. 화면을 펼친 뒤 새로고침하세요.');
 return {width:currentPixelWidth,height:currentPixelHeight};
}
function resizeReviewViewport(currentFieldGame,currentMapCanvas){
 const currentViewportSize=readReviewViewportSize(currentMapCanvas);
 if(currentFieldGame.scale.width!==currentViewportSize.width||currentFieldGame.scale.height!==currentViewportSize.height)currentFieldGame.scale.resize(currentViewportSize.width,currentViewportSize.height);
 currentMapCanvas.style.width='100%';currentMapCanvas.style.height='100%';
}

/** 화면 컨트롤·에셋 로딩은 어댑터, 면·UV·탑·오러 그리기는 공용 라이브러리가 소유한다. */
export async function createSharedFieldReview(currentMapCanvas,currentTextureImages,currentCharacterImage,currentCharacterRecord,currentGuardImages,currentSafeImages,currentTextureRecords=null,currentSelectedGameKeys={},currentFieldMapMode=false){
 let currentFieldScene;
 let currentHoverGraphic=null;
 let currentHoverLabel=null;
 let currentResolveReady;
 let currentRejectReady;
 let currentReviewDisposed=false;
 let currentExportInProgress=false;
 const currentReadyPromise=new Promise((currentResolveValue,currentRejectValue)=>{currentResolveReady=currentResolveValue;currentRejectReady=currentRejectValue;});
 const currentInitialSize=readReviewViewportSize(currentMapCanvas);
 const currentFieldGame=new Phaser.Game({type:Phaser.WEBGL,canvas:currentMapCanvas,width:currentInitialSize.width,height:currentInitialSize.height,scale:{mode:Phaser.Scale.NONE,zoom:1/GAME_INTERNAL_RESOLUTION_SCALE},render:{antialias:true,pixelArt:false,roundPixels:false},transparent:true,banner:false,audio:{noAudio:true},input:{mouse:false,touch:false,keyboard:false},scene:{create(){currentFieldScene=this;currentResolveReady();}}});
 function disposeSharedFieldReview(){
  if(currentReviewDisposed)return;
  currentReviewDisposed=true;
  window.removeEventListener('pagehide',disposeSharedFieldReview);
  currentFieldGame.destroy(false);
  currentRejectReady(Error('맵 검수 화면이 닫혔습니다.'));
 }
 window.addEventListener('pagehide',disposeSharedFieldReview,{once:true});
 try{
 await currentReadyPromise;
 if(currentReviewDisposed)throw Error('맵 검수 화면이 닫혔습니다.');
 currentMapCanvas.style.width='100%';currentMapCanvas.style.height='100%';
 for(const [currentTextureName,currentTextureImage] of Object.entries(currentTextureImages))currentFieldScene.textures.addImage(currentTextureName,currentTextureImage);
 for(const [currentGuardPath,currentGuardImage] of Object.entries(currentGuardImages))currentFieldScene.textures.addImage(currentGuardPath,currentGuardImage);
 for(const [currentSafeName,currentSafeImage] of Object.entries(currentSafeImages))currentFieldScene.textures.addImage('safe-'+currentSafeName,currentSafeImage);
 const currentCharacterTexture=currentFieldScene.textures.addImage('review-character',currentCharacterImage);
 const currentFrameRectangle=currentCharacterRecord.frame.rect;
 currentCharacterTexture.add('review-frame',0,currentFrameRectangle.x,currentFrameRectangle.y,currentFrameRectangle.width,currentFrameRectangle.height);
 let currentRenderSignature='';
 let currentFieldActorSignature='';
 let currentFieldActorObjects=[];
 let currentTownMapSignature='';
 let currentAppliedBuildingTextures=new Set();
 let currentTownActorSignature='';
 let currentTownActorObjects=[];
 let currentTownMeshObjects=[];
 let currentTownWaypointObjects=[];
 let currentFieldWaypointObjects=[];
 if(currentTextureRecords){
  for(const [currentGameTexture,currentCatalogKey] of Object.entries(currentSelectedGameKeys)){
   const currentTextureImage=currentTextureImages[currentCatalogKey];
   if(!currentTextureImage)throw Error('선택 맵 이미지가 없습니다: '+currentGameTexture);
   if(!currentFieldScene.textures.exists(currentGameTexture))currentFieldScene.textures.addImage(currentGameTexture,currentTextureImage);
  }
  if(!currentFieldMapMode)createTerrainAtlas(currentFieldScene,new Set(Object.keys(currentSelectedGameKeys)));
 }
 function drawSharedReviewActor(currentActorPoint,currentActorDepth){
  const currentCharacterAnchor=currentCharacterRecord.frame.anchor;
  const currentShadowGraphic=currentFieldScene.add.graphics().setDepth(currentActorDepth);
  drawCharacterContactShadow(currentShadowGraphic,currentActorPoint);
  const currentCharacterSprite=currentFieldScene.add.image(currentActorPoint.x,currentActorPoint.y,'review-character','review-frame').setOrigin(currentCharacterAnchor.x/currentFrameRectangle.width,currentCharacterAnchor.y/currentFrameRectangle.height).setScale(currentCharacterRecord.displayHeight/currentCharacterRecord.bodyHeight).setDepth(currentActorDepth+.01);
  currentCharacterSprite.setData('fieldActorVisibility',true);
  attachCharacterOutlineLayers(currentCharacterSprite);
 }
 function updateSharedReviewCamera(currentViewSettings){
  if(currentExportInProgress)return;
  resizeReviewViewport(currentFieldGame,currentMapCanvas);
  currentFieldScene.cameras.main.setOrigin(0,0).setZoom(currentViewSettings.scale*GAME_INTERNAL_RESOLUTION_SCALE).setScroll(-currentViewSettings.offsetX/currentViewSettings.scale,-currentViewSettings.offsetY/currentViewSettings.scale);
 }

 return {
  async exportWholeMapImage(currentGroundPoints){
   if(currentHoverGraphic?.scene)currentHoverGraphic.destroy();
   currentHoverGraphic=null;
   if(currentHoverLabel?.scene)currentHoverLabel.destroy();
   currentHoverLabel=null;
   if(currentExportInProgress)throw Error('이미지를 내보내는 중입니다. 완료 후 다시 시도하세요.');
   if(currentReviewDisposed)throw Error('맵 검수 화면이 닫혔습니다.');
   const currentCameraObject=currentFieldScene.cameras.main;
   const currentCameraState={width:currentFieldGame.scale.width,height:currentFieldGame.scale.height,zoom:currentCameraObject.zoom,x:currentCameraObject.scrollX,y:currentCameraObject.scrollY};
   const currentExtentPoints=[...currentGroundPoints];
   for(const currentSceneObject of currentFieldScene.children.list){
    if(!currentSceneObject.visible||typeof currentSceneObject.getBounds!=='function')continue;
    const currentObjectBounds=currentSceneObject.getBounds();
    currentExtentPoints.push({x:currentObjectBounds.left,y:currentObjectBounds.top},{x:currentObjectBounds.right,y:currentObjectBounds.bottom});
   }
   const currentMinimumX=Math.min(...currentExtentPoints.map(currentPointValue=>currentPointValue.x))-MAP_EXPORT_WORLD_PADDING;
   const currentMinimumY=Math.min(...currentExtentPoints.map(currentPointValue=>currentPointValue.y))-MAP_EXPORT_WORLD_PADDING;
   const currentWorldWidth=Math.max(...currentExtentPoints.map(currentPointValue=>currentPointValue.x))-currentMinimumX+MAP_EXPORT_WORLD_PADDING;
   const currentWorldHeight=Math.max(...currentExtentPoints.map(currentPointValue=>currentPointValue.y))-currentMinimumY+MAP_EXPORT_WORLD_PADDING;
   const currentExportScale=Math.min(1,MAP_EXPORT_MAXIMUM_EDGE/Math.max(currentWorldWidth,currentWorldHeight));
   currentExportInProgress=true;
   try{
    currentFieldGame.scale.resize(Math.ceil(currentWorldWidth*currentExportScale),Math.ceil(currentWorldHeight*currentExportScale));
    currentCameraObject.setZoom(currentExportScale).setScroll(currentMinimumX,currentMinimumY);
    return await new Promise((resolveExportImage,rejectExportImage)=>{
     const currentExportTimeout=setTimeout(()=>rejectExportImage(Error('이미지 내보내기 시간이 초과되었습니다. 다시 시도하세요.')),MAP_EXPORT_TIMEOUT_MS);
     currentFieldGame.renderer.snapshot(currentSnapshotImage=>{
      clearTimeout(currentExportTimeout);
      if(!currentSnapshotImage?.src){rejectExportImage(Error('맵 이미지 생성에 실패했습니다.'));return;}
      resolveExportImage(currentSnapshotImage);
     },'image/png');
    });
   }finally{
    currentFieldGame.scale.resize(currentCameraState.width,currentCameraState.height);
    currentCameraObject.setZoom(currentCameraState.zoom).setScroll(currentCameraState.x,currentCameraState.y);
    currentMapCanvas.style.width='100%';currentMapCanvas.style.height='100%';
    currentExportInProgress=false;
   }
  },
  showEditorHover(currentTargetRecord){
   if(currentHoverGraphic?.scene)currentHoverGraphic.destroy();
   currentHoverGraphic=null;
   if(currentHoverLabel?.scene)currentHoverLabel.destroy();
   currentHoverLabel=null;
   if(!currentTargetRecord)return;
   const currentTargetPoints=currentTargetRecord.points;
   currentHoverGraphic=currentFieldScene.add.graphics().setDepth(MAP_HOVER_OVERLAY_DEPTH);
   currentHoverGraphic.lineStyle(MAP_HOVER_BORDER_WIDTH/currentFieldScene.cameras.main.zoom*GAME_INTERNAL_RESOLUTION_SCALE,MAP_HOVER_OVERLAY_COLOR,1);
   currentHoverGraphic.fillStyle(MAP_HOVER_OVERLAY_COLOR,MAP_HOVER_OVERLAY_ALPHA);
   currentHoverGraphic.fillPoints(currentTargetPoints,true);
   currentHoverGraphic.strokePoints(currentTargetPoints,true);
   const currentLabelScale=GAME_INTERNAL_RESOLUTION_SCALE/currentFieldScene.cameras.main.zoom;
   const currentLabelText=`${currentTargetRecord.kind} (${currentTargetRecord.column}, ${currentTargetRecord.row})${currentTargetRecord.object?' · '+currentTargetRecord.object:''}`;
   currentHoverLabel=currentFieldScene.add.text(currentTargetPoints.reduce((currentPointSum,currentFacePoint)=>currentPointSum+currentFacePoint.x,0)/currentTargetPoints.length,Math.min(...currentTargetPoints.map(currentFacePoint=>currentFacePoint.y))-MAP_HOVER_LABEL_OFFSET*currentLabelScale,currentLabelText,MAP_HOVER_LABEL_STYLE).setOrigin(0.5,1).setScale(currentLabelScale).setDepth(MAP_HOVER_OVERLAY_DEPTH);
  },
  pickEditorBillboard(currentWorldPoint,currentIncludeGeometry=false){
   const currentSceneryImages=currentFieldScene.children.list.filter(currentRenderImage=>currentRenderImage.getData?.('mapEditorObjectRecord')).sort((currentFirstImage,currentSecondImage)=>currentSecondImage.depth-currentFirstImage.depth);
   for(const currentRenderImage of currentSceneryImages){
    const currentImageBounds=currentRenderImage.getBounds();
    if(!currentImageBounds.contains(currentWorldPoint.x,currentWorldPoint.y))continue;
    const currentPixelColumn=Math.floor((currentWorldPoint.x-currentImageBounds.x)/currentImageBounds.width*currentRenderImage.frame.width);
    const currentPixelRow=Math.floor((currentWorldPoint.y-currentImageBounds.y)/currentImageBounds.height*currentRenderImage.frame.height);
    if(currentFieldScene.textures.getPixelAlpha(currentPixelColumn,currentPixelRow,currentRenderImage.texture.key,currentRenderImage.frame.name)<32)continue;
    const currentObjectRecord=currentRenderImage.getData('mapEditorObjectRecord');
    return {...currentObjectRecord.position,object:currentObjectRecord.id,...(currentIncludeGeometry?{kind:'빌보드',points:[{x:currentImageBounds.left,y:currentImageBounds.top},{x:currentImageBounds.right,y:currentImageBounds.top},{x:currentImageBounds.right,y:currentImageBounds.bottom},{x:currentImageBounds.left,y:currentImageBounds.bottom}]}:{})};
   }
   return null;
  },
  addEditorTextures(currentNewImages,currentNewGameKeys){
   for(const [currentTextureName,currentTextureImage] of Object.entries(currentNewImages))if(!currentFieldScene.textures.exists(currentTextureName))currentFieldScene.textures.addImage(currentTextureName,currentTextureImage);
   for(const [currentGameTexture,currentCatalogKey] of Object.entries(currentNewGameKeys))if(!currentFieldScene.textures.exists(currentGameTexture))currentFieldScene.textures.addImage(currentGameTexture,currentNewImages[currentCatalogKey]);
   currentRenderSignature='';
  },
  render(currentFieldFrame,currentMapRecord,currentViewSettings){
   if(currentReviewDisposed)throw Error('맵 검수 화면이 닫혔습니다.');
   updateSharedReviewCamera(currentViewSettings);
   const currentNextSignature=JSON.stringify([currentMapRecord.id,currentFieldFrame.options.rotation,currentViewSettings.edges,currentViewSettings.tileEdges,currentViewSettings.blockedAreas,currentViewSettings.safe]);
   if(currentNextSignature!==currentRenderSignature){
    for(const currentRenderObject of [...currentFieldScene.children.list])if(currentRenderObject.scene)currentRenderObject.destroy();
    currentFieldActorSignature='';currentFieldActorObjects=[];currentFieldWaypointObjects=[];
    if(currentViewSettings.blockedAreas){
     const currentCellCenters=new Map(currentFieldFrame.cells.map(currentCellRecord=>[`${currentCellRecord.cell.column},${currentCellRecord.cell.row}`,currentCellRecord.center]));
     drawReviewBlockedAreas(currentFieldScene,currentMapRecord,currentCellPosition=>currentCellCenters.get(`${currentCellPosition.column},${currentCellPosition.row}`),currentFieldFrame.options.tileWidth,currentFieldFrame.options.tileHeight);
    }
    const currentSafeCenter=rotateSurfacePosition(currentMapRecord.startPoint,currentFieldFrame.options.rotation);
    for(const currentCellRecord of currentFieldFrame.cells){
     const currentTerrainName=currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentCellRecord.cell.row][currentCellRecord.cell.column]];
     const currentConnectionMask=['road','water'].includes(currentTerrainName)?readReviewConnectionMask(currentCellRecord.cell,currentMapRecord,currentTerrainName,currentFieldFrame.options.rotation):0;
     const currentTileTextures=resolveFieldTileTextures(currentFieldScene,currentTerrainName,currentCellRecord.cell,currentMapRecord.id,currentConnectionMask,currentCellPosition=>currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentCellPosition.row][currentCellPosition.column]],currentMapRecord.groundOverrides??[],currentMapRecord.groundDecals??[],currentMapRecord.cliffTextureKey,currentMapRecord.cliffOverrides??[]);
     const currentRenderDepth=resolveFieldSurfaceDepth(currentCellRecord.cell,currentMapRecord,currentFieldFrame.options);
     drawFieldCellObjects(currentFieldScene,currentCellRecord.cell,currentMapRecord,currentFieldFrame.options,currentTileTextures,currentRenderDepth,currentViewSettings.edges);
     if(currentViewSettings.tileEdges)drawReviewTileBoundary(currentFieldScene,currentCellRecord.center,currentFieldFrame.options.tileWidth,currentFieldFrame.options.tileHeight,currentRenderDepth+TERRAIN_DEPTH.surface+.01);
     if(currentViewSettings.safe){
      const currentViewCell=rotateSurfacePosition(currentCellRecord.cell,currentFieldFrame.options.rotation);
      for(const currentPanelPoints of buildFieldBoundaryPanels(currentViewCell,currentSafeCenter,currentMapRecord.safeRadius,currentCellRecord.center,currentFieldFrame.options)){
       drawFieldAuraPanel(currentFieldScene,currentPanelPoints,'safe-aura',currentRenderDepth+FIELD_REVIEW_ACTOR_DEPTH);
       if(currentViewSettings.edges)drawFieldMeshBoundary(currentFieldScene,currentPanelPoints,currentRenderDepth+FIELD_REVIEW_ACTOR_DEPTH+.1);
      }

     }
    }
    for(const currentObjectRecord of currentMapRecord.objects??[]){
     if(currentObjectRecord.kind==='ward-tower'&&!currentViewSettings.safe)continue;
     const currentObjectCell=currentFieldFrame.cells.find(currentCellRecord=>currentCellRecord.cell.column===currentObjectRecord.position.column&&currentCellRecord.cell.row===currentObjectRecord.position.row);
     if(!currentObjectCell)throw Error('지형지물 배치 좌표가 맵 범위를 벗어났습니다.');
     const currentObjectPlacement=resolveFieldSceneryPlacement(currentObjectRecord,currentObjectCell.center,currentFieldFrame.options);
     const currentObjectDepth=resolveFieldSceneryDepth(currentObjectRecord,currentMapRecord,currentFieldFrame.options);
     const currentSceneryResult=drawFieldSceneryObject(currentFieldScene,currentObjectRecord,currentObjectPlacement.screen,currentObjectDepth,'safe-tower',currentFieldFrame.options);
     if(currentObjectRecord.kind==='decoration')currentSceneryResult.setData('mapEditorObjectRecord',currentObjectRecord);
    }
    for(const currentGuardRecord of currentMapRecord.guardCenters??[]){
     const currentGuardPlacement=resolveGuardDisplayPlacement(currentGuardRecord.position,currentMapRecord);
     const currentGuardCenter=projectGuardDisplayCenter(currentGuardPlacement,currentCell=>{
      const currentFrameCell=currentFieldFrame.cells.find(currentRecord=>currentRecord.cell.column===currentCell.column&&currentRecord.cell.row===currentCell.row);
      if(!currentFrameCell)throw Error('경비센터 지면 렌더 셀이 없습니다.');
      return currentFrameCell.center;
     });
     const currentGuardDepth=resolveFieldSurfaceDepth(currentGuardPlacement.position,currentMapRecord,currentFieldFrame.options);
     const currentGuardImage=currentFieldScene.add.image(currentGuardCenter.x+currentGuardRecord.offsetX,currentGuardCenter.y+currentGuardRecord.offsetY,currentGuardRecord.path).setOrigin(currentGuardRecord.anchorX,currentGuardRecord.anchorY).setDepth(currentGuardDepth+FIELD_REVIEW_TOWER_DEPTH);
     currentGuardImage.setScale(currentFieldFrame.options.tileWidth*GUARD_CENTER_FOOTPRINT_SIZE/currentGuardImage.width);
    }
    for(const currentConnectionRecord of currentMapRecord.connections??[]){
     const currentWaypointCell=currentFieldFrame.cells.find(currentCellRecord=>currentCellRecord.cell.column===currentConnectionRecord.column&&currentCellRecord.cell.row===currentConnectionRecord.row);
     if(!currentWaypointCell)throw Error('웨이포인트가 맵 범위를 벗어났습니다.');
     currentFieldWaypointObjects.push(drawWaypoint(currentFieldScene,currentConnectionRecord,currentWaypointCell.center.x,currentWaypointCell.center.y).setDepth(mapAnnotationDepth(currentMapRecord)));
    }
    currentRenderSignature=currentNextSignature;
   }
   const currentActorSignature=JSON.stringify([currentViewSettings.character,currentViewSettings.characterCell]);
   if(currentActorSignature!==currentFieldActorSignature){
    for(const currentActorObject of currentFieldActorObjects)if(currentActorObject.scene)currentActorObject.destroy();
    const previousSceneObjects=new Set(currentFieldScene.children.list);
    const currentActorCell=currentFieldFrame.cells.find(currentCellRecord=>currentCellRecord.cell.column===currentViewSettings.characterCell.column&&currentCellRecord.cell.row===currentViewSettings.characterCell.row);
    if(currentViewSettings.character&&currentActorCell)drawSharedReviewActor(currentActorCell.center,resolveFieldSurfaceDepth(currentActorCell.cell,currentMapRecord,currentFieldFrame.options)+TERRAIN_DEPTH.actor);
    currentFieldActorObjects=currentFieldScene.children.list.filter(currentSceneObject=>!previousSceneObjects.has(currentSceneObject));
    currentFieldActorSignature=currentActorSignature;
   }
   for(const currentWaypointObject of currentFieldWaypointObjects)currentWaypointObject.setScale(waypointMarkerScale(currentViewSettings.scale));
   updateFieldActorOcclusion(currentFieldScene);
  },
  readAppliedBuildingTextures(){return [...currentAppliedBuildingTextures].sort();},
  renderTown(currentMapRecord,currentViewSettings,currentProjectPosition){
   if(currentReviewDisposed)throw Error('맵 검수 화면이 닫혔습니다.');
   const currentMapSignature=JSON.stringify([currentMapRecord.id,currentViewSettings.rotation,currentViewSettings.edges,currentViewSettings.tileEdges,currentViewSettings.blockedAreas]);
   const currentDepthPosition=currentCellPosition=>resolveFieldSurfaceDepth(currentCellPosition,currentMapRecord,{...FIELD_RENDER_METRICS,rotation:currentViewSettings.rotation});
   if(currentMapSignature!==currentTownMapSignature){
    for(const currentRenderObject of [...currentFieldScene.children.list])if(currentRenderObject.scene)currentRenderObject.destroy();
    currentAppliedBuildingTextures=new Set();
    currentTownActorObjects=[];currentTownMeshObjects=[];currentTownWaypointObjects=[];currentTownActorSignature='';
    const currentTileDimensions=resolveMapTileSize(currentMapRecord);
    for(let currentRowIndex=0;currentRowIndex<currentMapRecord.rows;currentRowIndex++)for(let currentColumnIndex=0;currentColumnIndex<currentMapRecord.columns;currentColumnIndex++){
     const currentCellPosition={column:currentColumnIndex,row:currentRowIndex};
     const currentTerrainName=currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentRowIndex][currentColumnIndex]];
     const currentScreenPoint=currentProjectPosition(currentCellPosition),currentCellDepth=currentDepthPosition(currentCellPosition);
     const currentConnectionMask=(currentTerrainName==='road'||currentTerrainName==='water')?readReviewConnectionMask(currentCellPosition,currentMapRecord,currentTerrainName,currentViewSettings.rotation):0;
     const currentFrameName=resolveReviewTownFrame(currentMapRecord,currentTerrainName,currentCellPosition,currentConnectionMask);
     if(!currentFieldScene.textures.get(TERRAIN_ATLAS).has(currentFrameName))throw Error('게임 타일 프레임 누락: '+currentFrameName);
     if(currentMapRecord.elevations?.some(currentHeightRow=>currentHeightRow.some(currentHeightValue=>currentHeightValue>0))){
      const currentTileTextures=resolveCityTileTextures(currentFieldScene,currentTerrainName,currentMapRecord.id,currentConnectionMask);
      drawFieldCellObjects(currentFieldScene,currentCellPosition,currentMapRecord,{...FIELD_RENDER_METRICS,tileWidth:currentTileDimensions.width,tileHeight:currentTileDimensions.height,originX:0,originY:0,rotation:0},currentTileTextures,currentCellDepth,currentViewSettings.edges);
     }else{
     currentFieldScene.add.image(currentScreenPoint.x,currentScreenPoint.y,TERRAIN_ATLAS,currentFrameName).setDisplaySize(currentTileDimensions.width,currentTileDimensions.height).setDepth(resolveCityGroundDepth(currentCellDepth,currentMapRecord)+TERRAIN_DEPTH.surface);
     drawTownMaterialEdges(currentFieldScene,currentCellPosition,currentNeighborCell=>currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentNeighborCell.row][currentNeighborCell.column]],currentProjectPosition,currentNeighborPosition=>resolveCityGroundDepth(currentDepthPosition(currentNeighborPosition),currentMapRecord),TERRAIN_DEPTH.surface);
     }
    }
    if(currentViewSettings.blockedAreas)drawReviewBlockedAreas(currentFieldScene,currentMapRecord,currentProjectPosition,currentTileDimensions.width,currentTileDimensions.height);
    if(currentViewSettings.tileEdges)for(let currentRowIndex=0;currentRowIndex<currentMapRecord.rows;currentRowIndex++)for(let currentColumnIndex=0;currentColumnIndex<currentMapRecord.columns;currentColumnIndex++){
     const currentTilePosition={column:currentColumnIndex,row:currentRowIndex};
     drawReviewTileBoundary(currentFieldScene,currentProjectPosition(currentTilePosition),currentTileDimensions.width,currentTileDimensions.height,resolveCityGroundDepth(currentDepthPosition(currentTilePosition),currentMapRecord)+TERRAIN_DEPTH.surface+.01);
    }
    for(const currentObjectRecord of currentMapRecord.objects??[]){
     const currentObjectPlacement=resolveFieldSceneryPlacement(currentObjectRecord,currentProjectPosition(currentObjectRecord.position),{tileWidth:currentTileDimensions.width,tileHeight:currentTileDimensions.height,rotation:currentViewSettings.rotation});
     drawFieldSceneryObject(currentFieldScene,currentObjectRecord,currentObjectPlacement.screen,resolveFieldSceneryDepth(currentObjectRecord,currentMapRecord,{tileWidth:currentTileDimensions.width,tileHeight:currentTileDimensions.height,rotation:currentViewSettings.rotation}),undefined,{tileWidth:currentTileDimensions.width,tileHeight:currentTileDimensions.height,rotation:currentViewSettings.rotation});
    }
    for(const currentBuildingRecord of currentMapRecord.buildings){
     const currentBuildingRegion=drawCityBuildingSprite(currentFieldScene,currentBuildingRecord,currentProjectPosition,currentDepthPosition,mapAnnotationDepth(currentMapRecord),false);
     if(!Array.isArray(currentBuildingRegion.appliedTextureIdentifiers))throw Error('공용 렌더러의 건물 원본 정보가 없습니다. 배포 버전을 확인하세요.');
     for(const currentTextureIdentifier of currentBuildingRegion.appliedTextureIdentifiers)currentAppliedBuildingTextures.add(currentTextureIdentifier);
     for(const currentBuildingPolygon of currentBuildingRegion.polygons)currentTownMeshObjects.push(drawFieldMeshBoundary(currentFieldScene,currentBuildingPolygon.points,currentBuildingRegion.depth+.02));
    }
    for(const currentConnectionRecord of currentMapRecord.connections){
     const currentWaypointPoint=currentProjectPosition(currentConnectionRecord);
     currentTownWaypointObjects.push(drawWaypoint(currentFieldScene,currentConnectionRecord,currentWaypointPoint.x,currentWaypointPoint.y).setDepth(mapAnnotationDepth(currentMapRecord)));
    }
    currentTownMapSignature=currentMapSignature;
   }
   const currentActorSignature=JSON.stringify([currentViewSettings.character,currentViewSettings.characterCell]);
   if(currentActorSignature!==currentTownActorSignature){
    for(const currentActorObject of currentTownActorObjects)if(currentActorObject.scene)currentActorObject.destroy();
    const previousSceneObjects=new Set(currentFieldScene.children.list);
    if(currentViewSettings.character)drawSharedReviewActor(currentProjectPosition(currentViewSettings.characterCell),currentDepthPosition(currentViewSettings.characterCell)+TERRAIN_DEPTH.actor);
    currentTownActorObjects=currentFieldScene.children.list.filter(currentSceneObject=>!previousSceneObjects.has(currentSceneObject));
    currentTownActorSignature=currentActorSignature;
   }
   for(const currentMeshGraphic of currentTownMeshObjects)currentMeshGraphic.setVisible(currentViewSettings.edges);
   updateSharedReviewCamera(currentViewSettings);
   updateFieldActorOcclusion(currentFieldScene);
   for(const currentWaypointObject of currentTownWaypointObjects)currentWaypointObject.setScale(waypointMarkerScale(currentViewSettings.scale));
  },
  destroy:disposeSharedFieldReview
 };
 }catch(currentInitializationError){
  disposeSharedFieldReview();
  throw currentInitializationError;
 }
}
