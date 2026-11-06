(currentFrameRows,currentTargetMode,currentTargetText,currentEditMode,currentLeftMargin,currentTopMargin,currentRightMargin,currentBottomMargin,currentAnchorX,currentAnchorY)=>{
 const currentOriginalRows=Array.isArray(currentFrameRows)?currentFrameRows:currentFrameRows?.data;
 try{
  if(!currentOriginalRows?.length)throw Error('시트를 먼저 불러오세요.');
  const currentEditedRows=currentOriginalRows.map(currentFrameRow=>currentFrameRow.map(Number));
  if(currentEditedRows.some(currentFrameRow=>currentFrameRow.length!==6||currentFrameRow.some(currentCellValue=>!Number.isSafeInteger(currentCellValue))))throw Error('프레임 좌표는 정수여야 합니다.');
  const currentTargetIndices=new Set();
  if(currentTargetMode==='전체')currentEditedRows.forEach((currentFrameRow,currentFrameIndex)=>currentTargetIndices.add(currentFrameIndex));
  else{
   if(!currentTargetText.trim())throw Error('프레임 번호를 입력하세요. 예: 1,3-5');
   for(const currentRangeText of currentTargetText.split(',')){
    const currentRangeMatch=currentRangeText.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/);
    if(!currentRangeMatch)throw Error('프레임 번호 형식 오류: 1,3-5처럼 입력하세요.');
    const currentRangeStart=Number(currentRangeMatch[1]),currentRangeEnd=Number(currentRangeMatch[2]??currentRangeMatch[1]);
    if(currentRangeStart<1||currentRangeEnd<currentRangeStart||currentRangeEnd>currentEditedRows.length)throw Error('프레임 번호 범위를 확인하세요.');
    for(let currentFrameNumber=currentRangeStart;currentFrameNumber<=currentRangeEnd;currentFrameNumber++)currentTargetIndices.add(currentFrameNumber-1);
   }
  }
  const currentEditValues=currentEditMode==='크롭'?[currentLeftMargin,currentTopMargin,currentRightMargin,currentBottomMargin]:[currentAnchorX,currentAnchorY];
  if(currentEditValues.some(currentCellValue=>!Number.isSafeInteger(currentCellValue)||(currentEditMode!=='크롭'&&currentCellValue<0)))throw Error('여백은 정수, 앵커는 0 이상의 정수여야 합니다.');
  for(const currentFrameIndex of currentTargetIndices){
   const currentFrameRow=currentEditedRows[currentFrameIndex];
   if(currentEditMode==='크롭'){
    currentFrameRow[0]+=currentLeftMargin;currentFrameRow[1]+=currentTopMargin;
    currentFrameRow[2]-=currentLeftMargin+currentRightMargin;currentFrameRow[3]-=currentTopMargin+currentBottomMargin;
    currentFrameRow[4]-=currentLeftMargin;currentFrameRow[5]-=currentTopMargin;
   }else{currentFrameRow[4]=currentAnchorX;currentFrameRow[5]=currentAnchorY;}
   if(currentFrameRow[2]<=0||currentFrameRow[3]<=0||currentFrameRow[4]<0||currentFrameRow[5]<0||currentFrameRow[4]>=currentFrameRow[2]||currentFrameRow[5]>=currentFrameRow[3])throw Error(`${currentFrameIndex+1}번 프레임의 크롭 크기 또는 앵커가 범위를 벗어납니다. 전체 적용을 취소했습니다.`);
  }
  return [{...(!Array.isArray(currentFrameRows)?currentFrameRows:{}),data:currentEditedRows},`${currentTargetIndices.size}개 프레임에 ${currentEditMode} 적용 · 미저장 편집입니다.`];
 }catch(currentEditError){return [currentFrameRows,currentEditError.message];}
}
