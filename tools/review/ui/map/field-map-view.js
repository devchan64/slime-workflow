import {resolveTownGroundFrame,resolveReedFrameForMap,drawWaypoint,waypointMarkerScale,resolveFieldTileTextures,collectTerrainTextureSources,createTerrainAtlas,TERRAIN_ATLAS,drawBlockStructure,cellDepth,TERRAIN_DEPTH,mapAnnotationDepth,resolveMapTileSize,resolveGrassFrameForMap,resolvePavingFrameForMap,selectFieldRoadFrame} from './vendor/field-renderer/1.0.25/town-renderer.mjs';
import {GAME_INTERNAL_RESOLUTION_SCALE,drawCharacterContactShadow,attachCharacterOutlineLayers,roadConnections,waterConnections} from './vendor/field-renderer/1.0.25/game-render-profile.mjs';
import * as Phaser from './vendor/field-renderer/1.0.25/phaser.mjs';
import {drawTownMaterialEdges,drawFieldCellObjects,drawFieldTowerObject,drawFieldAuraPanel,drawFieldMeshBoundary,buildFieldBoundaryPanels,rotateSurfacePosition} from './vendor/field-renderer/1.0.25/field-renderer.mjs';

const FIELD_REVIEW_ACTOR_DEPTH=TERRAIN_DEPTH.actor;
const FIELD_REVIEW_TOWER_DEPTH=TERRAIN_DEPTH.overlay;
const FIELD_REVIEW_TERRAIN_CACHE=new WeakMap();

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

/** 화면 컨트롤·에셋 로딩은 어댑터, 면·UV·탑·오러 그리기는 공용 라이브러리가 소유한다. */
export async function createSharedFieldReview(currentMapCanvas,currentTextureImages,currentCharacterImage,currentCharacterRecord,currentGuardImages,currentSafeImages,currentTextureRecords=null){
 let currentFieldScene;
 let currentResolveReady;
 const currentReadyPromise=new Promise(currentResolveValue=>{currentResolveReady=currentResolveValue;});
 const currentFieldGame=new Phaser.Game({type:Phaser.WEBGL,canvas:currentMapCanvas,width:currentMapCanvas.clientWidth*GAME_INTERNAL_RESOLUTION_SCALE,height:currentMapCanvas.clientHeight*GAME_INTERNAL_RESOLUTION_SCALE,scale:{mode:Phaser.Scale.NONE,zoom:1/GAME_INTERNAL_RESOLUTION_SCALE},render:{antialias:true,pixelArt:false,roundPixels:false},transparent:true,banner:false,audio:{noAudio:true},input:{mouse:false,touch:false,keyboard:false},scene:{create(){currentFieldScene=this;currentResolveReady();}}});
 await currentReadyPromise;
 currentMapCanvas.style.width='100%';currentMapCanvas.style.height='';
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
 let currentTownActorSignature='';
 let currentTownActorObjects=[];
 let currentTownMeshObjects=[];
 let currentTownWaypointObjects=[];
 if(currentTextureRecords){
  for(const [currentGameTexture,currentAssetPath] of Object.entries(collectTerrainTextureSources())){
   const currentCatalogEntry=Object.entries(currentTextureRecords).find(([,currentTileRecord])=>currentTileRecord.source===currentAssetPath);
   if(!currentCatalogEntry)throw Error('게임 타일 원본이 검수 카탈로그에 없습니다: '+currentAssetPath);
   currentFieldScene.textures.addImage(currentGameTexture,currentTextureImages[currentCatalogEntry[0]]);
  }
  createTerrainAtlas(currentFieldScene);
 }
 function drawSharedReviewActor(currentActorPoint,currentActorDepth){
  const currentCharacterAnchor=currentCharacterRecord.frame.anchor;
  const currentShadowGraphic=currentFieldScene.add.graphics().setDepth(currentActorDepth);
  drawCharacterContactShadow(currentShadowGraphic,currentActorPoint);
  const currentCharacterSprite=currentFieldScene.add.image(currentActorPoint.x,currentActorPoint.y,'review-character','review-frame').setOrigin(currentCharacterAnchor.x/currentFrameRectangle.width,currentCharacterAnchor.y/currentFrameRectangle.height).setScale(currentCharacterRecord.displayHeight/currentCharacterRecord.bodyHeight).setDepth(currentActorDepth+.01);
  attachCharacterOutlineLayers(currentCharacterSprite);
 }
 function updateSharedReviewCamera(currentViewSettings){
  const currentPixelWidth=currentMapCanvas.clientWidth*GAME_INTERNAL_RESOLUTION_SCALE,currentPixelHeight=currentMapCanvas.clientHeight*GAME_INTERNAL_RESOLUTION_SCALE;
  if(currentFieldGame.scale.width!==currentPixelWidth||currentFieldGame.scale.height!==currentPixelHeight)currentFieldGame.scale.resize(currentPixelWidth,currentPixelHeight);
  currentFieldScene.cameras.main.setOrigin(0,0).setZoom(currentViewSettings.scale*GAME_INTERNAL_RESOLUTION_SCALE).setScroll(-currentViewSettings.offsetX/currentViewSettings.scale,-currentViewSettings.offsetY/currentViewSettings.scale);
 }

 return {
  render(currentFieldFrame,currentMapRecord,currentViewSettings){
   if(currentFieldGame.scale.width!==currentMapCanvas.clientWidth*GAME_INTERNAL_RESOLUTION_SCALE||currentFieldGame.scale.height!==currentMapCanvas.clientHeight*GAME_INTERNAL_RESOLUTION_SCALE)currentFieldGame.scale.resize(currentMapCanvas.clientWidth*GAME_INTERNAL_RESOLUTION_SCALE,currentMapCanvas.clientHeight*GAME_INTERNAL_RESOLUTION_SCALE);
   const currentNextSignature=JSON.stringify([currentMapRecord.id,currentFieldFrame.options.rotation,currentViewSettings.edges,currentViewSettings.safe]);
   if(currentNextSignature!==currentRenderSignature){
    for(const currentRenderObject of [...currentFieldScene.children.list])if(currentRenderObject.scene)currentRenderObject.destroy();
    currentFieldActorSignature='';currentFieldActorObjects=[];
    const currentSafeCenter=rotateSurfacePosition(currentMapRecord.startPoint,currentFieldFrame.options.rotation);
    for(const currentCellRecord of currentFieldFrame.cells){
     const currentTerrainName=currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentCellRecord.cell.row][currentCellRecord.cell.column]];
     const currentConnectionMask=['road','water'].includes(currentTerrainName)?readReviewConnectionMask(currentCellRecord.cell,currentMapRecord,currentTerrainName,currentFieldFrame.options.rotation):0;
     const currentTileTextures=resolveFieldTileTextures(currentFieldScene,currentTerrainName,currentCellRecord.cell,currentMapRecord.id,currentConnectionMask,currentCellPosition=>currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentCellPosition.row][currentCellPosition.column]]);
     const currentRenderDepth=cellDepth(rotateSurfacePosition(currentCellRecord.cell,currentFieldFrame.options.rotation));
     drawFieldCellObjects(currentFieldScene,currentCellRecord.cell,currentMapRecord,currentFieldFrame.options,currentTileTextures,currentRenderDepth,currentViewSettings.edges);
     if(currentViewSettings.safe){
      const currentViewCell=rotateSurfacePosition(currentCellRecord.cell,currentFieldFrame.options.rotation);
      for(const currentPanelPoints of buildFieldBoundaryPanels(currentViewCell,currentSafeCenter,currentMapRecord.safeRadius,currentCellRecord.center,currentFieldFrame.options)){
       drawFieldAuraPanel(currentFieldScene,currentPanelPoints,'safe-aura',currentRenderDepth+FIELD_REVIEW_ACTOR_DEPTH);
       if(currentViewSettings.edges)drawFieldMeshBoundary(currentFieldScene,currentPanelPoints,currentRenderDepth+FIELD_REVIEW_ACTOR_DEPTH+.1);
      }
      if(currentCellRecord.cell.column===currentMapRecord.startPoint.column&&currentCellRecord.cell.row===currentMapRecord.startPoint.row)drawFieldTowerObject(currentFieldScene,currentCellRecord.center,'safe-tower',currentRenderDepth+FIELD_REVIEW_TOWER_DEPTH);
     }
     for(const currentGuardRecord of currentMapRecord.guardCenters??[]){
      if(currentGuardRecord.renderPosition.column!==currentCellRecord.cell.column||currentGuardRecord.renderPosition.row!==currentCellRecord.cell.row)continue;
      const currentGuardImage=currentFieldScene.add.image(currentCellRecord.center.x+currentGuardRecord.offsetX,currentCellRecord.center.y+currentGuardRecord.offsetY,currentGuardRecord.path).setOrigin(currentGuardRecord.anchorX,currentGuardRecord.anchorY).setDepth(currentRenderDepth+FIELD_REVIEW_ACTOR_DEPTH);
      currentGuardImage.setScale(currentGuardRecord.displayWidth/currentGuardImage.width);
     }
    }
    currentRenderSignature=currentNextSignature;
   }
   const currentActorSignature=JSON.stringify([currentViewSettings.character,currentViewSettings.characterCell]);
   if(currentActorSignature!==currentFieldActorSignature){
    for(const currentActorObject of currentFieldActorObjects)if(currentActorObject.scene)currentActorObject.destroy();
    const previousSceneObjects=new Set(currentFieldScene.children.list);
    const currentActorCell=currentFieldFrame.cells.find(currentCellRecord=>currentCellRecord.cell.column===currentViewSettings.characterCell.column&&currentCellRecord.cell.row===currentViewSettings.characterCell.row);
    if(currentViewSettings.character&&currentActorCell)drawSharedReviewActor(currentActorCell.center,cellDepth(rotateSurfacePosition(currentActorCell.cell,currentFieldFrame.options.rotation))+TERRAIN_DEPTH.actor);
    currentFieldActorObjects=currentFieldScene.children.list.filter(currentSceneObject=>!previousSceneObjects.has(currentSceneObject));
    currentFieldActorSignature=currentActorSignature;
   }
   currentFieldScene.cameras.main.setOrigin(0,0).setZoom(currentViewSettings.scale*GAME_INTERNAL_RESOLUTION_SCALE).setScroll(-currentViewSettings.offsetX/currentViewSettings.scale,-currentViewSettings.offsetY/currentViewSettings.scale);
  },
  renderTown(currentMapRecord,currentViewSettings,currentProjectPosition){
   const currentMapSignature=JSON.stringify([currentMapRecord.id,currentViewSettings.rotation]);
   const currentDepthPosition=currentCellPosition=>cellDepth(rotateSurfacePosition(currentCellPosition,currentViewSettings.rotation));
   if(currentMapSignature!==currentTownMapSignature){
    for(const currentRenderObject of [...currentFieldScene.children.list])if(currentRenderObject.scene)currentRenderObject.destroy();
    currentTownActorObjects=[];currentTownMeshObjects=[];currentTownWaypointObjects=[];currentTownActorSignature='';
    const currentTileDimensions=resolveMapTileSize(currentMapRecord);
    for(let currentRowIndex=0;currentRowIndex<currentMapRecord.rows;currentRowIndex++)for(let currentColumnIndex=0;currentColumnIndex<currentMapRecord.columns;currentColumnIndex++){
     const currentCellPosition={column:currentColumnIndex,row:currentRowIndex};
     const currentTerrainName=currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentRowIndex][currentColumnIndex]];
     const currentScreenPoint=currentProjectPosition(currentCellPosition),currentCellDepth=currentDepthPosition(currentCellPosition);
     const currentConnectionMask=(currentTerrainName==='road'||currentTerrainName==='water')?readReviewConnectionMask(currentCellPosition,currentMapRecord,currentTerrainName,currentViewSettings.rotation):0;
     const currentFrameName=currentTerrainName==='water'?`water-${currentConnectionMask}`:currentTerrainName==='road'?selectFieldRoadFrame(currentConnectionMask,currentCellPosition,true,currentMapRecord.id):currentTerrainName==='reed-bed'?resolveReedFrameForMap(currentMapRecord.id):currentTerrainName==='paving'?resolvePavingFrameForMap(currentMapRecord.id):currentTerrainName==='grass'?resolveGrassFrameForMap(currentMapRecord.id):resolveTownGroundFrame(currentMapRecord.id,currentTerrainName);
     if(!currentFieldScene.textures.get(TERRAIN_ATLAS).has(currentFrameName))throw Error('게임 타일 프레임 누락: '+currentFrameName);
     currentFieldScene.add.image(currentScreenPoint.x,currentScreenPoint.y,TERRAIN_ATLAS,currentFrameName).setDisplaySize(currentTileDimensions.width,currentTileDimensions.height).setDepth(currentCellDepth+TERRAIN_DEPTH.surface);
     drawTownMaterialEdges(currentFieldScene,currentCellPosition,currentNeighborCell=>currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentNeighborCell.row][currentNeighborCell.column]],currentProjectPosition,currentDepthPosition,TERRAIN_DEPTH.surface);
    }
    for(const currentBuildingRecord of currentMapRecord.buildings){
     const currentBuildingRegion=drawBlockStructure(currentFieldScene,currentBuildingRecord,currentProjectPosition,currentDepthPosition,mapAnnotationDepth(currentMapRecord),false);
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
   for(const currentWaypointObject of currentTownWaypointObjects)currentWaypointObject.setScale(waypointMarkerScale(currentViewSettings.scale));
  },
  destroy(){currentFieldGame.destroy(false);}
 };
}
