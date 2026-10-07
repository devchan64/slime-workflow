import {collectTerrainTextureSources,createTerrainAtlas,TERRAIN_ATLAS,drawBlockStructure,cellDepth,TERRAIN_DEPTH,mapAnnotationDepth,resolveMapTileSize,resolveGrassFrameForMap,resolvePavingFrameForMap,selectFieldRoadFrame} from './vendor/field-renderer/1.0.9/town-renderer.mjs';
import {GAME_INTERNAL_RESOLUTION_SCALE,CHARACTER_CONTACT_SHADOW_COLOR,CHARACTER_CONTACT_SHADOW_ALPHA_SCALE,attachCharacterOutlineLayers,roadConnections,waterConnections} from './vendor/field-renderer/1.0.9/game-render-profile.mjs';
import * as Phaser from './vendor/field-renderer/1.0.9/phaser.mjs';
import {drawFieldCellObjects,drawFieldTowerObject,drawFieldAuraPanel,drawFieldMeshBoundary,buildFieldBoundaryPanels,resolveFieldActorContactShadow,rotateSurfacePosition,prepareFieldConnectedTexture} from './vendor/field-renderer/1.0.9/field-renderer.mjs';

const FIELD_REVIEW_DEPTH_SCALE=5;
const FIELD_REVIEW_DEPTH_BASE=100;
const FIELD_REVIEW_ACTOR_DEPTH=20;
const FIELD_REVIEW_TOWER_DEPTH=10;
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
 let currentTownMapSignature='';
 let currentTownActorSignature='';
 let currentTownActorObjects=[];
 let currentTownMeshObjects=[];
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
  const currentShadowMetrics=resolveFieldActorContactShadow('contrast');
  for(const currentShadowLayer of [currentShadowMetrics.outer,currentShadowMetrics.core]){currentShadowGraphic.fillStyle(CHARACTER_CONTACT_SHADOW_COLOR,Math.min(1,currentShadowLayer.alpha*CHARACTER_CONTACT_SHADOW_ALPHA_SCALE));currentShadowGraphic.fillEllipse(currentActorPoint.x,currentActorPoint.y,currentShadowLayer.width,currentShadowLayer.height);}
  const currentCharacterSprite=currentFieldScene.add.image(currentActorPoint.x,currentActorPoint.y,'review-character','review-frame').setOrigin(currentCharacterAnchor.x/currentFrameRectangle.width,currentCharacterAnchor.y/currentFrameRectangle.height).setScale(currentCharacterRecord.displayHeight/currentCharacterRecord.bodyHeight).setDepth(currentActorDepth+.01);
  attachCharacterOutlineLayers(currentCharacterSprite);
 }
 function updateSharedReviewCamera(currentViewSettings){
  const currentPixelWidth=currentMapCanvas.clientWidth*GAME_INTERNAL_RESOLUTION_SCALE,currentPixelHeight=currentMapCanvas.clientHeight*GAME_INTERNAL_RESOLUTION_SCALE;
  if(currentFieldGame.scale.width!==currentPixelWidth||currentFieldGame.scale.height!==currentPixelHeight)currentFieldGame.scale.resize(currentPixelWidth,currentPixelHeight);
  currentFieldScene.cameras.main.setOrigin(0,0).setZoom(currentViewSettings.scale*GAME_INTERNAL_RESOLUTION_SCALE).setScroll(-currentViewSettings.offsetX/currentViewSettings.scale,-currentViewSettings.offsetY/currentViewSettings.scale);
 }

 return {
  render(currentFieldFrame,currentMapRecord,currentTextureNames,currentViewSettings){
   if(currentFieldGame.scale.width!==currentMapCanvas.clientWidth*GAME_INTERNAL_RESOLUTION_SCALE||currentFieldGame.scale.height!==currentMapCanvas.clientHeight*GAME_INTERNAL_RESOLUTION_SCALE)currentFieldGame.scale.resize(currentMapCanvas.clientWidth*GAME_INTERNAL_RESOLUTION_SCALE,currentMapCanvas.clientHeight*GAME_INTERNAL_RESOLUTION_SCALE);
   const currentNextSignature=JSON.stringify([currentFieldFrame.options.rotation,currentViewSettings.edges,currentViewSettings.safe,currentViewSettings.character,currentViewSettings.characterCell]);
   if(currentNextSignature!==currentRenderSignature){
    for(const currentRenderObject of [...currentFieldScene.children.list])if(currentRenderObject.scene)currentRenderObject.destroy();
    const currentSafeCenter=rotateSurfacePosition(currentMapRecord.startPoint,currentFieldFrame.options.rotation);
    for(const currentCellRecord of currentFieldFrame.cells){
     const currentTerrainName=currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentCellRecord.cell.row][currentCellRecord.cell.column]];
     let currentGroundKey=currentTextureNames[currentTerrainName];
     const currentGrassKey=currentTextureNames.grass;
     if(currentTerrainName==='water'||(currentTerrainName==='road'&&currentMapRecord.id!=='meadow'))currentGroundKey=prepareFieldConnectedTexture(currentFieldScene,currentGroundKey,currentGrassKey,readReviewConnectionMask(currentCellRecord.cell,currentMapRecord,currentTerrainName,currentFieldFrame.options.rotation));
     const currentRenderDepth=FIELD_REVIEW_DEPTH_BASE+currentCellRecord.depth*FIELD_REVIEW_DEPTH_SCALE;
     drawFieldCellObjects(currentFieldScene,currentCellRecord.cell,currentMapRecord,currentFieldFrame.options,{ground:currentGroundKey,resolveGroundMaterial:currentCellPosition=>currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentCellPosition.row][currentCellPosition.column]],cliff:'cliff-wall',tread:'ramp-tread',roadConnectionMask:currentTerrainName==='road'?readReviewConnectionMask(currentCellRecord.cell,currentMapRecord,'road',currentFieldFrame.options.rotation):undefined,fullTileRoad:currentMapRecord.id==='meadow',underlay:['boulder','tree-base'].includes(currentTerrainName)?currentGrassKey:undefined},currentRenderDepth,currentViewSettings.edges);
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
     if(currentViewSettings.character&&currentCellRecord.cell.column===currentViewSettings.characterCell.column&&currentCellRecord.cell.row===currentViewSettings.characterCell.row){
      drawSharedReviewActor(currentCellRecord.center,currentRenderDepth+FIELD_REVIEW_ACTOR_DEPTH);
     }
    }
    currentRenderSignature=currentNextSignature;
   }
   currentFieldScene.cameras.main.setOrigin(0,0).setZoom(currentViewSettings.scale*GAME_INTERNAL_RESOLUTION_SCALE).setScroll(-currentViewSettings.offsetX/currentViewSettings.scale,-currentViewSettings.offsetY/currentViewSettings.scale);
  },
  renderTown(currentMapRecord,currentViewSettings,currentProjectPosition){
   const currentMapSignature=JSON.stringify([currentMapRecord.id,currentViewSettings.rotation]);
   const currentDepthPosition=currentCellPosition=>cellDepth(rotateSurfacePosition(currentCellPosition,currentViewSettings.rotation));
   if(currentMapSignature!==currentTownMapSignature){
    for(const currentRenderObject of [...currentFieldScene.children.list])if(currentRenderObject.scene)currentRenderObject.destroy();
    currentTownActorObjects=[];currentTownMeshObjects=[];currentTownActorSignature='';
    const currentTileDimensions=resolveMapTileSize(currentMapRecord);
    for(let currentRowIndex=0;currentRowIndex<currentMapRecord.rows;currentRowIndex++)for(let currentColumnIndex=0;currentColumnIndex<currentMapRecord.columns;currentColumnIndex++){
     const currentCellPosition={column:currentColumnIndex,row:currentRowIndex};
     const currentTerrainName=currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentRowIndex][currentColumnIndex]];
     const currentScreenPoint=currentProjectPosition(currentCellPosition),currentCellDepth=currentDepthPosition(currentCellPosition);
     const currentConnectionMask=(currentTerrainName==='road'||currentTerrainName==='water')?readReviewConnectionMask(currentCellPosition,currentMapRecord,currentTerrainName,currentViewSettings.rotation):0;
     const currentFrameName=currentTerrainName==='water'?`water-${currentConnectionMask}`:currentTerrainName==='road'?selectFieldRoadFrame(currentConnectionMask,currentCellPosition,true,currentMapRecord.id):currentTerrainName==='paving'?resolvePavingFrameForMap(currentMapRecord.id):currentTerrainName==='grass'?resolveGrassFrameForMap(currentMapRecord.id):currentTerrainName;
     if(!currentFieldScene.textures.get(TERRAIN_ATLAS).has(currentFrameName))throw Error('게임 타일 프레임 누락: '+currentFrameName);
     currentFieldScene.add.image(currentScreenPoint.x,currentScreenPoint.y,TERRAIN_ATLAS,currentFrameName).setDisplaySize(currentTileDimensions.width,currentTileDimensions.height).setDepth(currentCellDepth+TERRAIN_DEPTH.surface);
    }
    for(const currentBuildingRecord of currentMapRecord.buildings){
     const currentBuildingRegion=drawBlockStructure(currentFieldScene,currentBuildingRecord,currentProjectPosition,currentDepthPosition,mapAnnotationDepth(currentMapRecord),false);
     for(const currentBuildingPolygon of currentBuildingRegion.polygons)currentTownMeshObjects.push(drawFieldMeshBoundary(currentFieldScene,currentBuildingPolygon.points,currentBuildingRegion.depth+.02));
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
  },
  destroy(){currentFieldGame.destroy(false);}
 };
}
