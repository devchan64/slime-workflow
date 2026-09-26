// 검수용 캐릭터 위치만 변경한다. 원본 맵과 게임 상태를 수정하지 않는다.
(()=>{
 let selectedMapDocument=null,selectedMapRecord=null,characterPreviewData=null;
 let characterWorldPosition=null,currentRotationDegrees=0,characterDirectionName='down_left';
 const mapImageElement=document.querySelector('#map-preview');
 const mapContainerElement=mapImageElement.parentElement;
 const characterImageElement=document.createElement('img');
 characterImageElement.alt='기본 캐릭터 · 60px 크기 비교';characterImageElement.hidden=true;
 Object.assign(characterImageElement.style,{position:'absolute',pointerEvents:'none',maxWidth:'none',zIndex:'2'});
 mapContainerElement.append(characterImageElement);
 const characterStatusElement=document.createElement('p');characterStatusElement.setAttribute('role','status');
 characterStatusElement.textContent='맵의 이동 가능한 칸을 클릭하면 기본 캐릭터를 배치합니다. 캐릭터는 크기 비교용으로 맵 위에 표시됩니다.';
 mapContainerElement.before(characterStatusElement);
 const rotateCellPosition=(cellPositionValue,rotationDegreesValue)=>{
  const mapSizeValue=selectedMapDocument.grid.columns;
  const {column:columnIndexValue,row:rowIndexValue}=cellPositionValue;
  if(rotationDegreesValue===90)return {column:mapSizeValue-1-rowIndexValue,row:columnIndexValue};
  if(rotationDegreesValue===180)return {column:mapSizeValue-1-columnIndexValue,row:mapSizeValue-1-rowIndexValue};
  if(rotationDegreesValue===270)return {column:rowIndexValue,row:mapSizeValue-1-columnIndexValue};
  return {...cellPositionValue};
 };
 window.updateMapCharacterPreview=rotationDegreesValue=>{
  currentRotationDegrees=rotationDegreesValue;
  if(!characterPreviewData||!characterWorldPosition||!mapImageElement.naturalWidth)return;
  const currentViewPosition=rotateCellPosition(characterWorldPosition,currentRotationDegrees);
  const viewDirectionNames=['down_left','up_left','up_right','down_right'];
  const currentFrameRecord=characterPreviewData.directions[viewDirectionNames[(viewDirectionNames.indexOf(characterDirectionName)+currentRotationDegrees/90)%4]];
  const currentZoomScale=mapImageElement.getBoundingClientRect().width/mapImageElement.naturalWidth;
  const currentCharacterScale=selectedMapRecord.render_profile.character_height/characterPreviewData.body_height*currentZoomScale;
  const halfTileWidth=selectedMapRecord.render_profile.tile_width/2,halfTileHeight=selectedMapRecord.render_profile.tile_height/2;
  const currentFootPosition={x:selectedMapDocument.grid.rows*halfTileWidth+(currentViewPosition.column-currentViewPosition.row)*halfTileWidth,y:(currentViewPosition.column+currentViewPosition.row+1)*halfTileHeight+characterPreviewData.top_padding};
  characterImageElement.src=currentFrameRecord.file;
  characterImageElement.style.width=currentFrameRecord.width*currentCharacterScale+'px';
  characterImageElement.style.height=currentFrameRecord.height*currentCharacterScale+'px';
  characterImageElement.style.left=mapImageElement.offsetLeft+currentFootPosition.x*currentZoomScale-currentFrameRecord.anchor.x*currentCharacterScale+'px';
  characterImageElement.style.top=mapImageElement.offsetTop+currentFootPosition.y*currentZoomScale-currentFrameRecord.anchor.y*currentCharacterScale+'px';
  characterImageElement.hidden=false;
  characterImageElement.dataset.column=characterWorldPosition.column;characterImageElement.dataset.row=characterWorldPosition.row;
 };
 window.configureMapCharacterPreview=(mapDocumentValue,mapRecordValue)=>{selectedMapDocument=mapDocumentValue;selectedMapRecord=mapRecordValue;characterWorldPosition={...mapDocumentValue.spawn};characterDirectionName='down_left';window.updateMapCharacterPreview(0);};
 mapImageElement.addEventListener('click',pointerEventValue=>{
  if(!characterPreviewData||!selectedMapDocument)return;
  const imageBoundsValue=mapImageElement.getBoundingClientRect();
  const currentZoomScale=imageBoundsValue.width/mapImageElement.naturalWidth;
  const horizontalPointValue=(pointerEventValue.clientX-imageBoundsValue.left)/currentZoomScale;
  const verticalPointValue=(pointerEventValue.clientY-imageBoundsValue.top)/currentZoomScale-characterPreviewData.top_padding;
  const horizontalCellValue=horizontalPointValue/(selectedMapRecord.render_profile.tile_width/2)-selectedMapDocument.grid.rows;
  const verticalCellValue=verticalPointValue/(selectedMapRecord.render_profile.tile_height/2);
  const clickedViewPosition={column:Math.floor((verticalCellValue+horizontalCellValue)/2),row:Math.floor((verticalCellValue-horizontalCellValue)/2)};
  if(clickedViewPosition.column<0||clickedViewPosition.row<0||clickedViewPosition.column>=selectedMapDocument.grid.columns||clickedViewPosition.row>=selectedMapDocument.grid.rows)return;
  const selectedWorldPosition=rotateCellPosition(clickedViewPosition,(360-currentRotationDegrees)%360);
  if(selectedMapDocument.collision.some(cellRecordValue=>cellRecordValue.column===selectedWorldPosition.column&&cellRecordValue.row===selectedWorldPosition.row)){characterStatusElement.textContent='이동할 수 없는 칸입니다. 바닥의 이동 가능한 칸을 선택하세요.';return;}
  const columnDistanceValue=selectedWorldPosition.column-characterWorldPosition.column,rowDistanceValue=selectedWorldPosition.row-characterWorldPosition.row;
  if(columnDistanceValue||rowDistanceValue)characterDirectionName=Math.abs(columnDistanceValue)>Math.abs(rowDistanceValue)?(columnDistanceValue>0?'down_right':'up_left'):(rowDistanceValue>0?'down_left':'up_right');
  characterWorldPosition=selectedWorldPosition;
  window.updateMapCharacterPreview(currentRotationDegrees);
  characterStatusElement.textContent=`캐릭터 위치 · 열 ${selectedWorldPosition.column}, 행 ${selectedWorldPosition.row} · 기준 60px · 크기 비교용 배치`;
 });
 new ResizeObserver(()=>window.updateMapCharacterPreview(currentRotationDegrees)).observe(mapImageElement);
 fetch('character-preview.json').then(async responseValue=>{if(!responseValue.ok)throw Error('캐릭터 검수 데이터 조회 실패');characterPreviewData=await responseValue.json();window.updateMapCharacterPreview(currentRotationDegrees);}).catch(errorValue=>{characterStatusElement.textContent=errorValue.message;});
})();
