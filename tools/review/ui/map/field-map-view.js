import * as Phaser from './vendor/field-renderer/1.0.2/phaser.mjs';
import {drawFieldCellObjects,drawFieldTowerObject,drawFieldAuraPanel,drawFieldMeshBoundary,buildFieldBoundaryPanels,rotateSurfacePosition,prepareFieldConnectedTexture} from './vendor/field-renderer/1.0.2/field-renderer.mjs';

const FIELD_REVIEW_DEPTH_SCALE=5;
const FIELD_REVIEW_DEPTH_BASE=100;
const FIELD_REVIEW_ACTOR_DEPTH=20;
const FIELD_REVIEW_TOWER_DEPTH=10;
const FIELD_REVIEW_NEIGHBORS=[{column:0,row:-1,bit:1},{column:1,row:0,bit:2},{column:0,row:1,bit:4},{column:-1,row:0,bit:8}];

function readReviewConnectionMask(currentCellPosition,currentMapRecord,currentTerrainName,currentRotationValue){
 let currentConnectionMask=0;
 for(const currentNeighborEntry of FIELD_REVIEW_NEIGHBORS){
  const currentNeighborColumn=currentCellPosition.column+currentNeighborEntry.column,currentNeighborRow=currentCellPosition.row+currentNeighborEntry.row;
  const currentNeighborCode=currentMapRecord.terrainRows[currentNeighborRow]?.[currentNeighborColumn];
  if(currentMapRecord.terrainCodes[currentNeighborCode]===currentTerrainName&&currentMapRecord.elevations[currentNeighborRow][currentNeighborColumn]===currentMapRecord.elevations[currentCellPosition.row][currentCellPosition.column])currentConnectionMask|=currentNeighborEntry.bit;
 }
 for(let currentTurnIndex=0;currentTurnIndex<currentRotationValue;currentTurnIndex++)currentConnectionMask=((currentConnectionMask<<1)&15)|(currentConnectionMask>>3);
 return currentConnectionMask;
}

/** 화면 컨트롤·에셋 로딩은 어댑터, 면·UV·탑·오러 그리기는 공용 라이브러리가 소유한다. */
export async function createSharedFieldReview(currentMapCanvas,currentTextureImages,currentCharacterImage,currentCharacterRecord,currentGuardImages,currentSafeImages){
 let currentFieldScene;
 let currentResolveReady;
 const currentReadyPromise=new Promise(currentResolveValue=>{currentResolveReady=currentResolveValue;});
 const currentFieldGame=new Phaser.Game({type:Phaser.WEBGL,canvas:currentMapCanvas,width:currentMapCanvas.clientWidth,height:currentMapCanvas.clientHeight,transparent:true,banner:false,audio:{noAudio:true},input:{mouse:false,touch:false,keyboard:false},scene:{create(){currentFieldScene=this;currentResolveReady();}}});
 await currentReadyPromise;
 currentMapCanvas.style.width='100%';currentMapCanvas.style.height='';
 for(const [currentTextureName,currentTextureImage] of Object.entries(currentTextureImages))currentFieldScene.textures.addImage(currentTextureName,currentTextureImage);
 for(const [currentGuardPath,currentGuardImage] of Object.entries(currentGuardImages))currentFieldScene.textures.addImage(currentGuardPath,currentGuardImage);
 for(const [currentSafeName,currentSafeImage] of Object.entries(currentSafeImages))currentFieldScene.textures.addImage('safe-'+currentSafeName,currentSafeImage);
 const currentCharacterTexture=currentFieldScene.textures.addImage('review-character',currentCharacterImage);
 const currentFrameRectangle=currentCharacterRecord.frame.rect;
 currentCharacterTexture.add('review-frame',0,currentFrameRectangle.x,currentFrameRectangle.y,currentFrameRectangle.width,currentFrameRectangle.height);
 let currentRenderSignature='';
 return {
  render(currentFieldFrame,currentMapRecord,currentTextureNames,currentViewSettings){
   if(currentFieldGame.scale.width!==currentMapCanvas.clientWidth||currentFieldGame.scale.height!==currentMapCanvas.clientHeight)currentFieldGame.scale.resize(currentMapCanvas.clientWidth,currentMapCanvas.clientHeight);
   const currentNextSignature=JSON.stringify([currentFieldFrame.options.rotation,currentViewSettings.edges,currentViewSettings.safe,currentViewSettings.character,currentViewSettings.characterCell]);
   if(currentNextSignature!==currentRenderSignature){
    for(const currentRenderObject of [...currentFieldScene.children.list])currentRenderObject.destroy();
    const currentSafeCenter=rotateSurfacePosition(currentMapRecord.startPoint,currentFieldFrame.options.rotation);
    for(const currentCellRecord of currentFieldFrame.cells){
     const currentTerrainName=currentMapRecord.terrainCodes[currentMapRecord.terrainRows[currentCellRecord.cell.row][currentCellRecord.cell.column]];
     let currentGroundKey=currentTextureNames[currentTerrainName];
     if(currentTerrainName==='water'||(currentTerrainName==='road'&&currentMapRecord.id!=='meadow'))currentGroundKey=prepareFieldConnectedTexture(currentFieldScene,currentGroundKey,currentTextureNames.grass,readReviewConnectionMask(currentCellRecord.cell,currentMapRecord,currentTerrainName,currentFieldFrame.options.rotation));
     const currentRenderDepth=FIELD_REVIEW_DEPTH_BASE+currentCellRecord.depth*FIELD_REVIEW_DEPTH_SCALE;
     drawFieldCellObjects(currentFieldScene,currentCellRecord.cell,currentMapRecord,currentFieldFrame.options,{ground:currentGroundKey,cliff:'cliff-wall',tread:'ramp-tread',underlay:['boulder','tree-base'].includes(currentTerrainName)?currentTextureNames.grass:undefined},currentRenderDepth,currentViewSettings.edges);
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
      const currentCharacterAnchor=currentCharacterRecord.frame.anchor;
      currentFieldScene.add.image(currentCellRecord.center.x,currentCellRecord.center.y,'review-character','review-frame').setOrigin(currentCharacterAnchor.x/currentFrameRectangle.width,currentCharacterAnchor.y/currentFrameRectangle.height).setScale(currentCharacterRecord.displayHeight/currentCharacterRecord.bodyHeight).setDepth(currentRenderDepth+FIELD_REVIEW_ACTOR_DEPTH);
     }
    }
    currentRenderSignature=currentNextSignature;
   }
   currentFieldScene.cameras.main.setOrigin(0,0).setZoom(currentViewSettings.scale).setScroll(-currentViewSettings.offsetX/currentViewSettings.scale,-currentViewSettings.offsetY/currentViewSettings.scale);
  },
  destroy(){currentFieldGame.destroy(false);}
 };
}
