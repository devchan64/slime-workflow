const SOURCE_PREVIEW_TILE_FILL='#ffffff';
const SOURCE_PREVIEW_GUIDE_STYLE=Object.freeze({fill:SOURCE_PREVIEW_TILE_FILL,stroke:'#808080',dash:[5,4],lineWidth:1});
/** 원본 픽셀 크기와 타일 접지 영역을 비교하는 검수 캔버스. */
const SOURCE_PREVIEW_WIDTH=768;
const SOURCE_PREVIEW_HEIGHT=260;
const SOURCE_PREVIEW_VERTICAL_SCALE=1.5;
const SOURCE_PREVIEW_PADDING=100;
export function installSourceSizePreview(currentTextureRecords,currentSelectedGameKeys,currentMapRecord,currentRenderMetrics){
 if(!Number.isFinite(currentRenderMetrics?.tileWidth)||!Number.isFinite(currentRenderMetrics?.tileHeight)||currentRenderMetrics.tileWidth<=0||currentRenderMetrics.tileHeight<=0)throw Error("공통 타일 렌더 규격이 필요합니다.");
 let currentPreviewVersion=0;
 const currentSharedProperties=currentMapRecord.spriteProperties??{};
 const findAnchorEntries=currentGameKey=>[...(currentMapRecord.objects??[]).filter(currentObjectRecord=>currentObjectRecord.textureKey===currentGameKey).map(currentObjectRecord=>({id:currentObjectRecord.id,anchorX:currentObjectRecord.anchorX??0.5,anchorY:currentObjectRecord.anchorY??1,groundFootprintColumns:currentObjectRecord.groundFootprintColumns??1,groundFootprintRows:currentObjectRecord.groundFootprintRows??1,displayHeight:currentObjectRecord.displayHeight})),...(currentMapRecord.buildings??[]).filter(currentBuildingRecord=>currentBuildingRecord.sprite?.textureKey===currentGameKey).map(currentBuildingRecord=>({id:currentBuildingRecord.id,anchorX:currentBuildingRecord.sprite.anchorX??0.5,anchorY:currentBuildingRecord.sprite.anchorY??1}))];
 window.mapSourceAnchorRead=currentGameKey=>{const currentAssetProperties=currentSharedProperties[currentGameKey]??findAnchorEntries(currentGameKey)[0];if((currentMapRecord.objects??[]).some(currentObjectRecord=>currentObjectRecord.textureKey===currentGameKey)&&!currentSharedProperties[currentGameKey])throw Error('빌보드 공용 속성이 없습니다. 검수 화면을 새로고침하세요.');return [currentAssetProperties?.anchorX??0.5,currentAssetProperties?.anchorY??1,currentAssetProperties?.groundFootprintColumns??1,currentAssetProperties?.groundFootprintRows??1,currentAssetProperties?.displayHeight??128];};
 window.mapSourceEditorRead=currentGameKey=>{
  const currentAnchorEntries=findAnchorEntries(currentGameKey),currentEditableAnchor=currentAnchorEntries.length>0,currentEditableLayout=currentAnchorEntries.some(currentAnchorEntry=>currentAnchorEntry.displayHeight!==undefined);
  return [...window.mapSourceAnchorRead(currentGameKey).map((currentControlValue,currentControlIndex)=>({__type__:'update',value:currentControlValue,interactive:currentControlIndex<2?currentEditableAnchor:currentEditableLayout})),{__type__:'update',interactive:currentEditableAnchor}];
 };
 window.mapSourceAnchorPayload=(currentGameKey,currentAnchorX,currentAnchorY,currentFootprintColumns,currentFootprintRows,currentDisplayHeight)=>({map:currentMapRecord.id,kind:currentMapRecord.safeTown===false?'field':'town',texture:currentGameKey,anchorX:currentAnchorX,anchorY:currentAnchorY,expected:currentSharedProperties[currentGameKey]?{...currentSharedProperties[currentGameKey]}:null,...((currentMapRecord.objects??[]).some(currentObjectRecord=>currentObjectRecord.textureKey===currentGameKey)?{layout:{groundFootprintColumns:currentFootprintColumns,groundFootprintRows:currentFootprintRows,displayHeight:currentDisplayHeight}}:{})});
 window.mapSourceAnchorCommitted=currentSaveResult=>{
  if(!currentSaveResult?.saved)return;
  const currentSavedPayload=currentSaveResult.payload;
  if(currentSavedPayload.map!==currentMapRecord.id)return;
  currentSharedProperties[currentSavedPayload.texture]={...currentSharedProperties[currentSavedPayload.texture],anchorX:currentSavedPayload.anchorX,anchorY:currentSavedPayload.anchorY,...currentSavedPayload.layout};
  const currentSavedAnchors={anchorX:currentSavedPayload.anchorX,anchorY:currentSavedPayload.anchorY};
  for(const currentObjectRecord of currentMapRecord.objects??[]){
   if(currentObjectRecord.textureKey===currentSavedPayload.texture)Object.assign(currentObjectRecord,currentSavedAnchors,currentSavedPayload.layout??{});
  }
  for(const currentBuildingRecord of currentMapRecord.buildings??[]){
   if(currentBuildingRecord.sprite?.textureKey===currentSavedPayload.texture)Object.assign(currentBuildingRecord.sprite,currentSavedAnchors);
  }
 };
 let currentUnifiedEntries=[];
 const currentStructureRecords={};
 window.mapSourceUnifiedList=(currentSourceCategory='all',currentSearchText='')=>{
  const currentCategoryLabels={tiles:'지형 타일',buildings:'건물',vegetation:'자연물','large-trees':'큰 나무','rocks-minerals':'암석광물',props:'소품',structures:'결계·경비 구조물'};
  const currentSourceEntries=Object.entries(currentSelectedGameKeys).map(([currentGameKey,currentCatalogKey])=>{
   const currentAssetRecord=currentTextureRecords[currentCatalogKey],currentSourcePath=currentAssetRecord.source;
   const currentAssetCategory=(currentMapRecord.buildings??[]).some(currentBuildingRecord=>currentBuildingRecord.sprite?.textureKey===currentGameKey)?'buildings':(currentMapRecord.objects??[]).some(currentObjectRecord=>currentObjectRecord.textureKey===currentGameKey)||currentSourcePath.includes('/billboards/')?currentAssetRecord.billboard_category:currentSourcePath.includes('/tiles/')?'tiles':'structures';
   if(!currentCategoryLabels[currentAssetCategory])throw Error('에셋 분류 누락: '+currentCatalogKey);
   return {key:currentGameKey,name:currentCatalogKey,path:new URL(currentAssetRecord.path,location.href).href,category:currentAssetCategory,size:currentAssetRecord.source_size?.join(' × ')??'확인 필요'};
  });
  for(const currentStructureImage of document.querySelectorAll('#applied-structure-list img')){
   const currentStructureKey='structure:'+currentStructureImage.src;
   if(currentSourceEntries.some(currentSourceEntry=>currentSourceEntry.key===currentStructureKey))continue;
   currentStructureRecords[currentStructureKey]={path:currentStructureImage.src};
   currentSourceEntries.push({key:currentStructureKey,path:currentStructureImage.src,name:currentStructureImage.parentElement.textContent,category:'structures',size:currentStructureImage.naturalWidth?`${currentStructureImage.naturalWidth} × ${currentStructureImage.naturalHeight}`:'확인 필요'});
  }
  currentUnifiedEntries=currentSourceEntries.filter(currentSourceEntry=>(currentSourceCategory==='all'||currentSourceEntry.category===currentSourceCategory)&&currentSourceEntry.name.toLowerCase().includes(currentSearchText.trim().toLowerCase()));
  return [currentUnifiedEntries.map(currentSourceEntry=>({image:{path:currentSourceEntry.path,url:currentSourceEntry.path,meta:{_type:'gradio.FileData'}},caption:`${currentSourceEntry.name} · ${currentCategoryLabels[currentSourceEntry.category]} · ${currentSourceEntry.size} px`})), '', ''];
 };
 window.mapSourceUnifiedSelect=currentSelectedIndex=>{
  const currentSelectedEntry=currentUnifiedEntries[currentSelectedIndex];
  if(!currentSelectedEntry)throw Error('목록이 변경되었습니다. 원본을 다시 선택하세요.');
  return [currentSelectedEntry.key,currentSelectedEntry.name];
 };
 window.mapSourceResizePreview=async(currentGameKey,currentTargetSize,currentAnchorX=null,currentAnchorY=null,currentFootprintColumns=1,currentFootprintRows=1,currentDisplayOverride=null)=>{
  const currentRequestVersion=++currentPreviewVersion;
  if(!currentGameKey){const currentPreviewCanvas=document.querySelector('#map-source-size-preview');currentPreviewCanvas?.getContext('2d').clearRect(0,0,currentPreviewCanvas.width,currentPreviewCanvas.height);return [{},'원본을 선택하면 저장할 수 있습니다. 결계·경비 구조물은 원본 목록에서 확인하세요.',{__type__:'update',interactive:false}];}
  const currentAssetRecord=currentStructureRecords[currentGameKey]??currentTextureRecords[currentSelectedGameKeys[currentGameKey]];
  const currentSourceImage=new Image();currentSourceImage.src=new URL(currentAssetRecord.path,location.href).href;await currentSourceImage.decode();
  if(currentRequestVersion!==currentPreviewVersion)return [{__type__:'update'},{__type__:'update'},{__type__:'update'}];
  const currentPreviewCanvas=document.querySelector('#map-source-size-preview');
  const currentCanvasContext=currentPreviewCanvas.getContext('2d');
  if(currentStructureRecords[currentGameKey]){
   currentPreviewCanvas.width=SOURCE_PREVIEW_WIDTH;currentPreviewCanvas.height=SOURCE_PREVIEW_HEIGHT;
   const currentImageScale=Math.min(1,SOURCE_PREVIEW_WIDTH/currentSourceImage.width,SOURCE_PREVIEW_HEIGHT/currentSourceImage.height);
   currentCanvasContext.drawImage(currentSourceImage,0,0,currentSourceImage.width*currentImageScale,currentSourceImage.height*currentImageScale);
   return [{},`구조물 원본 ${currentSourceImage.width}×${currentSourceImage.height}px · 읽기 전용입니다.`,{__type__:'update',interactive:false}];
  }

  currentPreviewCanvas.width=SOURCE_PREVIEW_WIDTH;currentPreviewCanvas.height=SOURCE_PREVIEW_HEIGHT;
  const currentPlacementRecord=(currentMapRecord.objects??[]).find(currentObjectRecord=>currentObjectRecord.textureKey===currentGameKey);
  const currentBuildingRecord=(currentMapRecord.buildings??[]).find(currentBuildingRecord=>currentBuildingRecord.sprite?.textureKey===currentGameKey);
  const currentAnchorRecord=currentPlacementRecord??currentBuildingRecord?.sprite??{};
  const currentTargetRatio=Number(currentTargetSize)/Math.max(currentSourceImage.width,currentSourceImage.height);
  const currentTargetWidth=Math.round(currentSourceImage.width*currentTargetRatio),currentTargetHeight=Math.round(currentSourceImage.height*currentTargetRatio);
  const currentDisplayHeight=currentPlacementRecord?((currentDisplayOverride??currentPlacementRecord.displayHeight)*(currentRenderMetrics.billboardScale??1)):(currentBuildingRecord?((currentBuildingRecord.width+currentBuildingRecord.height)*currentRenderMetrics.tileWidth/2*1.04/(currentAnchorRecord.contentWidth??1))*currentSourceImage.height/currentSourceImage.width:128);
  const currentDisplayWidth=currentDisplayHeight*(currentRenderMetrics.imageAspectRatio??currentSourceImage.width/currentSourceImage.height);
  const currentReducedCanvas=document.createElement('canvas');currentReducedCanvas.width=currentTargetWidth;currentReducedCanvas.height=currentTargetHeight;
  const currentReducedContext=currentReducedCanvas.getContext('2d');currentReducedContext.imageSmoothingQuality='high';currentReducedContext.drawImage(currentSourceImage,0,0,currentTargetWidth,currentTargetHeight);
  const currentGroundPreview=drawAssetGroundPreview(currentPreviewCanvas,currentReducedCanvas,{anchorX:currentAnchorX??currentAnchorRecord.anchorX??.5,anchorY:currentAnchorY??currentAnchorRecord.anchorY??1,groundFootprintColumns:Number(currentFootprintColumns),groundFootprintRows:Number(currentFootprintRows),displayHeight:currentDisplayHeight,billboardAnchorMode:currentAnchorRecord.billboardAnchorMode,billboardPlacementAnchor:currentAnchorRecord.billboardPlacementAnchor},{...currentRenderMetrics,billboardScale:1,imageAspectRatio:currentSourceImage.width/currentSourceImage.height});
  return [{path:currentAssetRecord.source,sha256:currentAssetRecord.sha256,size:Number(currentTargetSize)},`원본 ${currentSourceImage.width}×${currentSourceImage.height}px → ${currentTargetWidth}×${currentTargetHeight}px. 노랑: 바닥 선언 ${currentFootprintColumns}×${currentFootprintRows} · 실제 점유 ${currentGroundPreview.occupiedCells}칸, 파랑: 이미지 영역, 빨강: 접지 앵커. 맵 표시 크기 ${Math.round(currentDisplayWidth)}×${Math.round(currentDisplayHeight)}px 유지 · 원본 해상도만 변경합니다.${Number(currentTargetSize)>Math.max(currentSourceImage.width,currentSourceImage.height)?' 확대 저장 불가: 원본 이하 크기를 선택하세요.':''}${currentBuildingRecord?' 건물은 여러 타일을 점유할 수 있습니다.':''}`,{__type__:'update',interactive:Number(currentTargetSize)<=Math.max(currentSourceImage.width,currentSourceImage.height)}];
 };
}

/** 맵 검수·공용 에셋 편집기가 공유하는 실제 배율·점유 셀 미리보기. */
export function drawAssetGroundPreview(currentPreviewCanvas,currentSourceImage,currentPropertyValues,currentRenderMetrics){
 const currentIntersectionMode=currentPropertyValues.billboardAnchorMode==='tile-intersection';
 const currentColumnDistance=currentPropertyValues.groundFootprintColumns===1?.5:currentPropertyValues.groundFootprintColumns-1;
 const currentRowDistance=currentPropertyValues.groundFootprintRows===1?.5:currentPropertyValues.groundFootprintRows-1;
 const currentTileWidth=currentRenderMetrics.tileWidth,currentTileHeight=currentRenderMetrics.tileHeight;
 const currentDisplayHeight=currentPropertyValues.displayHeight*(currentRenderMetrics.billboardScale??1),currentDisplayWidth=currentDisplayHeight*(currentRenderMetrics.imageAspectRatio??currentSourceImage.width/currentSourceImage.height);
 const currentColumnRadius=currentPropertyValues.groundFootprintColumns-1,currentRowRadius=currentPropertyValues.groundFootprintRows-1;
 const currentGroundPadding=(currentColumnRadius+currentRowRadius+4)*currentTileHeight/2;
 currentPreviewCanvas.width=Math.max(SOURCE_PREVIEW_WIDTH,currentDisplayWidth*2+SOURCE_PREVIEW_PADDING*2,(currentColumnRadius+currentRowRadius+4)*currentTileWidth);
 currentPreviewCanvas.height=Math.max(SOURCE_PREVIEW_HEIGHT,currentDisplayHeight+currentGroundPadding*2);
 const currentImageBelowGround=currentDisplayHeight*(1-currentPropertyValues.anchorY)+currentTileHeight/2;
 currentPreviewCanvas.height=Math.ceil((currentPreviewCanvas.height+Math.max(0,currentImageBelowGround-currentGroundPadding))*SOURCE_PREVIEW_VERTICAL_SCALE);
 const currentGroundCenterX=currentPreviewCanvas.width/2,currentGroundCenterY=currentPreviewCanvas.height-Math.max(currentGroundPadding,currentImageBelowGround);
 const currentAnchorOffset=currentPropertyValues.billboardPlacementAnchor==='top'?-1:currentPropertyValues.billboardPlacementAnchor==='bottom'?1:0;
 const currentTileAnchorMode=['tile-bottom-center','tile-intersection'].includes(currentPropertyValues.billboardAnchorMode);
 const currentIntersectionX=currentGroundCenterX+(currentColumnDistance-currentRowDistance)*currentTileWidth/2,currentIntersectionY=currentGroundCenterY+(currentColumnDistance+currentRowDistance)*currentTileHeight/2;
 const currentAnchorPositionX=currentIntersectionMode?currentIntersectionX+currentPropertyValues.anchorX*currentTileWidth:currentGroundCenterX+(currentTileAnchorMode?(currentPropertyValues.anchorX-.5)*currentTileWidth:0);
 const currentAnchorPositionY=currentIntersectionMode?currentIntersectionY+currentPropertyValues.anchorY*currentTileHeight:currentGroundCenterY+(currentTileAnchorMode?(currentPropertyValues.anchorY-.5)*currentTileHeight:currentAnchorOffset*currentTileHeight/2);
 const currentCanvasContext=currentPreviewCanvas.getContext('2d');currentCanvasContext.clearRect(0,0,currentPreviewCanvas.width,currentPreviewCanvas.height);
 const currentPreviewZoom=currentRenderMetrics.previewZoom??1;
 const currentViewCenterY=(Math.min(currentAnchorPositionY-currentDisplayHeight*(currentTileAnchorMode?1:currentPropertyValues.anchorY),currentGroundCenterY-currentGroundPadding)+Math.max(currentAnchorPositionY+currentDisplayHeight*(currentTileAnchorMode?0:1-currentPropertyValues.anchorY),currentGroundCenterY+currentGroundPadding))/2;
 currentCanvasContext.save();
 currentCanvasContext.translate(currentPreviewCanvas.width/2,currentPreviewCanvas.height/2);
 currentCanvasContext.scale(currentPreviewZoom,currentPreviewZoom);
 currentCanvasContext.translate(-currentGroundCenterX,-currentViewCenterY);
 const currentTilePaths=[];
 for(let currentColumnOffset=0;currentColumnOffset<=currentColumnRadius;currentColumnOffset++)for(let currentRowOffset=0;currentRowOffset<=currentRowRadius;currentRowOffset++){
  const currentCenterX=currentGroundCenterX+(currentColumnOffset-currentRowOffset)*currentTileWidth/2,currentCenterY=currentGroundCenterY+(currentColumnOffset+currentRowOffset)*currentTileHeight/2;
  const currentTilePath=new Path2D();currentTilePath.moveTo(currentCenterX,currentCenterY-currentTileHeight/2);currentTilePath.lineTo(currentCenterX+currentTileWidth/2,currentCenterY);currentTilePath.lineTo(currentCenterX,currentCenterY+currentTileHeight/2);currentTilePath.lineTo(currentCenterX-currentTileWidth/2,currentCenterY);currentTilePath.closePath();currentTilePaths.push(currentTilePath);currentCanvasContext.fillStyle=SOURCE_PREVIEW_TILE_FILL;currentCanvasContext.fill(currentTilePath);
 }
 // 2×2 이하 점유만 2×2 보조 격자로 교차점 주변 그림자를 검수한다.
 const currentAnchorGuidePaths=[];
 if(currentTileAnchorMode&&currentColumnRadius<=1&&currentRowRadius<=1){
  for(let currentColumnOffset=0;currentColumnOffset<=1;currentColumnOffset++)for(let currentRowOffset=0;currentRowOffset<=1;currentRowOffset++){
   const currentGuideCenterX=currentGroundCenterX+(currentColumnOffset-currentRowOffset)*currentTileWidth/2,currentGuideCenterY=currentGroundCenterY+(currentColumnOffset+currentRowOffset)*currentTileHeight/2;
   const currentGuideTilePath=new Path2D();currentGuideTilePath.moveTo(currentGuideCenterX,currentGuideCenterY-currentTileHeight/2);currentGuideTilePath.lineTo(currentGuideCenterX+currentTileWidth/2,currentGuideCenterY);currentGuideTilePath.lineTo(currentGuideCenterX,currentGuideCenterY+currentTileHeight/2);currentGuideTilePath.lineTo(currentGuideCenterX-currentTileWidth/2,currentGuideCenterY);currentGuideTilePath.closePath();
   currentAnchorGuidePaths.push(currentGuideTilePath);currentCanvasContext.fillStyle=SOURCE_PREVIEW_GUIDE_STYLE.fill;currentCanvasContext.fill(currentGuideTilePath);
  }
 }
 if(currentRenderMetrics.drawShadow){
  const currentPreviewGraphics={setDepth(){return this;},fillStyle(currentColorValue,currentAlphaValue){currentCanvasContext.fillStyle='#'+currentColorValue.toString(16).padStart(6,'0');currentCanvasContext.globalAlpha=currentAlphaValue;},fillEllipse(currentCenterX,currentCenterY,currentWidthValue,currentHeightValue){currentCanvasContext.beginPath();currentCanvasContext.ellipse(currentCenterX,currentCenterY,currentWidthValue/2,currentHeightValue/2,0,0,Math.PI*2);currentCanvasContext.fill();},fillPoints(currentPointRecords){currentCanvasContext.beginPath();currentPointRecords.forEach((currentPointRecord,currentPointIndex)=>currentPointIndex?currentCanvasContext.lineTo(currentPointRecord.x,currentPointRecord.y):currentCanvasContext.moveTo(currentPointRecord.x,currentPointRecord.y));currentCanvasContext.closePath();currentCanvasContext.fill();}};
  currentRenderMetrics.drawShadow({add:{graphics:()=>currentPreviewGraphics}},currentPropertyValues,{x:currentAnchorPositionX,y:currentAnchorPositionY},0,currentRenderMetrics);
  currentCanvasContext.globalAlpha=1;
 }
 if(currentAnchorGuidePaths.length){
  currentCanvasContext.save();currentCanvasContext.strokeStyle=SOURCE_PREVIEW_GUIDE_STYLE.stroke;currentCanvasContext.lineWidth=SOURCE_PREVIEW_GUIDE_STYLE.lineWidth;currentCanvasContext.setLineDash(SOURCE_PREVIEW_GUIDE_STYLE.dash);currentAnchorGuidePaths.forEach(currentGuideTilePath=>currentCanvasContext.stroke(currentGuideTilePath));currentCanvasContext.restore();
 }
 const currentImageLeft=currentAnchorPositionX-currentDisplayWidth*(currentTileAnchorMode?.5:currentPropertyValues.anchorX),currentImageTop=currentAnchorPositionY-currentDisplayHeight*(currentTileAnchorMode?1:currentPropertyValues.anchorY);
 currentCanvasContext.drawImage(currentSourceImage,currentImageLeft,currentImageTop,currentDisplayWidth,currentDisplayHeight);
 currentCanvasContext.lineWidth=2;currentTilePaths.forEach((currentTilePath,currentTileIndex)=>{const currentColumnOffset=Math.floor(currentTileIndex/(currentRowRadius+1)),currentRowOffset=currentTileIndex%(currentRowRadius+1);const currentBlockedCell=currentRenderMetrics.showBlockedAreas!==false&&currentColumnOffset>0&&currentColumnOffset<currentColumnRadius&&currentRowOffset>0&&currentRowOffset<currentRowRadius;if(currentBlockedCell){currentCanvasContext.fillStyle='rgba(255,65,55,0.35)';currentCanvasContext.fill(currentTilePath);}currentCanvasContext.strokeStyle=currentBlockedCell?'#ff7168':'#ffd859';currentCanvasContext.stroke(currentTilePath);});
 // 3×2 가운데 두 셀의 공유 경계는 타일 전체 차단과 구분한다.
 if(currentRenderMetrics.showBlockedAreas!==false&&currentColumnRadius===2&&currentRowRadius===1){
  const currentBoundaryCenterX=currentGroundCenterX+currentTileWidth/4,currentBoundaryCenterY=currentGroundCenterY+3*currentTileHeight/4;
  currentCanvasContext.strokeStyle='#ff7168';currentCanvasContext.lineWidth=3;currentCanvasContext.beginPath();
  currentCanvasContext.moveTo(currentBoundaryCenterX-currentTileWidth/4,currentBoundaryCenterY-currentTileHeight/4);
  currentCanvasContext.lineTo(currentBoundaryCenterX+currentTileWidth/4,currentBoundaryCenterY+currentTileHeight/4);currentCanvasContext.stroke();
 }
 currentCanvasContext.strokeStyle='#75cfff';currentCanvasContext.strokeRect(currentImageLeft,currentImageTop,currentDisplayWidth,currentDisplayHeight);
 currentCanvasContext.fillStyle='#ff7168';currentCanvasContext.beginPath();currentCanvasContext.arc(currentAnchorPositionX,currentAnchorPositionY,4,0,Math.PI*2);currentCanvasContext.fill();
 currentCanvasContext.restore();
 return {width:currentDisplayWidth,height:currentDisplayHeight,occupiedCells:currentTilePaths.length};
}
