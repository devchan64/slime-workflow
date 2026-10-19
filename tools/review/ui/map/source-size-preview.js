/** 원본 픽셀 크기와 타일 접지 영역을 비교하는 검수 캔버스. */
const SOURCE_PREVIEW_WIDTH=768;
const SOURCE_PREVIEW_HEIGHT=260;
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
  const currentCategoryLabels={tiles:'지형 타일',buildings:'건물',vegetation:'자연물',props:'소품',structures:'결계·경비 구조물'};
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
  const currentDisplayWidth=currentDisplayHeight*currentSourceImage.width/currentSourceImage.height;
  const currentReducedCanvas=document.createElement('canvas');currentReducedCanvas.width=currentTargetWidth;currentReducedCanvas.height=currentTargetHeight;
  const currentReducedContext=currentReducedCanvas.getContext('2d');currentReducedContext.imageSmoothingQuality='high';currentReducedContext.drawImage(currentSourceImage,0,0,currentTargetWidth,currentTargetHeight);
  const currentGroundPadding=(Number(currentFootprintColumns)+Number(currentFootprintRows))*currentRenderMetrics.tileHeight/4+SOURCE_PREVIEW_PADDING/2;
  currentPreviewCanvas.height=Math.max(SOURCE_PREVIEW_HEIGHT,currentDisplayHeight+currentGroundPadding*2);
  const currentGroundCenterX=SOURCE_PREVIEW_WIDTH/2,currentGroundCenterY=currentPreviewCanvas.height-currentGroundPadding;
  currentCanvasContext.clearRect(0,0,SOURCE_PREVIEW_WIDTH,currentPreviewCanvas.height);
  const currentHalfColumns=Number(currentFootprintColumns)/2,currentHalfRows=Number(currentFootprintRows)/2;
  const currentTileVertices=[[-currentHalfColumns,-currentHalfRows],[currentHalfColumns,-currentHalfRows],[currentHalfColumns,currentHalfRows],[-currentHalfColumns,currentHalfRows]].map(([currentColumnOffset,currentRowOffset])=>[currentGroundCenterX+(currentColumnOffset-currentRowOffset)*currentRenderMetrics.tileWidth/2,currentGroundCenterY+(currentColumnOffset+currentRowOffset)*currentRenderMetrics.tileHeight/2]);
  currentCanvasContext.beginPath();currentTileVertices.forEach(([currentVertexX,currentVertexY],currentVertexIndex)=>currentVertexIndex?currentCanvasContext.lineTo(currentVertexX,currentVertexY):currentCanvasContext.moveTo(currentVertexX,currentVertexY));currentCanvasContext.closePath();currentCanvasContext.fillStyle='#506655';currentCanvasContext.fill();
  const currentImageLeft=currentGroundCenterX-currentDisplayWidth*(currentAnchorX??currentAnchorRecord.anchorX??0.5),currentImageTop=currentGroundCenterY-currentDisplayHeight*(currentAnchorY??currentAnchorRecord.anchorY??1);
  currentCanvasContext.drawImage(currentReducedCanvas,currentImageLeft,currentImageTop,currentDisplayWidth,currentDisplayHeight);
  currentCanvasContext.strokeStyle='#ffd859';currentCanvasContext.lineWidth=2;currentCanvasContext.stroke();
  currentCanvasContext.strokeStyle='#75cfff';currentCanvasContext.strokeRect(currentImageLeft,currentImageTop,currentDisplayWidth,currentDisplayHeight);
  currentCanvasContext.fillStyle='#ff7168';currentCanvasContext.beginPath();currentCanvasContext.arc(currentGroundCenterX,currentGroundCenterY,4,0,Math.PI*2);currentCanvasContext.fill();
  return [{path:currentAssetRecord.source,sha256:currentAssetRecord.sha256,size:Number(currentTargetSize)},`원본 ${currentSourceImage.width}×${currentSourceImage.height}px → ${currentTargetWidth}×${currentTargetHeight}px. 노랑: 바닥 ${currentFootprintColumns}×${currentFootprintRows}칸, 파랑: 이미지 영역, 빨강: 접지 앵커. 맵 표시 크기 ${Math.round(currentDisplayWidth)}×${Math.round(currentDisplayHeight)}px 유지 · 원본 해상도만 변경합니다.${Number(currentTargetSize)>Math.max(currentSourceImage.width,currentSourceImage.height)?' 확대 저장 불가: 원본 이하 크기를 선택하세요.':''}${currentBuildingRecord?' 건물은 여러 타일을 점유할 수 있습니다.':''}`,{__type__:'update',interactive:Number(currentTargetSize)<=Math.max(currentSourceImage.width,currentSourceImage.height)}];
 };
}
