(currentFrameRows,currentTargetMode,currentSelectedFrames,currentOperation)=>{
 const currentCanvasElement=document.getElementById('sprite-sheet-alignment-preview');
 const currentEditorState=currentCanvasElement?.spriteEditorState;
 try{
  const currentRows=(Array.isArray(currentFrameRows)?currentFrameRows:currentFrameRows?.data)?.map(currentRow=>currentRow.map(Number));
  if(!currentEditorState||JSON.stringify(currentRows)!==currentEditorState.signature)throw Error('시트를 불러오고 미리보기를 확인하세요.');
  const formatCurrentRows=currentValues=>({...(!Array.isArray(currentFrameRows)?currentFrameRows:{}),data:currentValues});
  if(currentOperation==='discard'){
   currentEditorState.drafts={};
   return [currentFrameRows,'적용 전 드래그를 취소했습니다. 반영된 좌표는 유지됩니다.'];
  }
  if(currentOperation==='undo'){
   if(!currentEditorState.undo.length)throw Error('실행 취소할 적용 이력이 없습니다.');
   const currentPreviousRows=currentEditorState.undo.pop();currentEditorState.expectedSignature=JSON.stringify(currentPreviousRows);
   return [formatCurrentRows(currentPreviousRows),'직전 캔버스 적용을 취소했습니다.'];
  }
  const currentOriginalRow=currentRows[currentEditorState.index],currentDraftRow=currentEditorState.drafts[currentEditorState.index];
  if(!currentDraftRow||JSON.stringify(currentDraftRow)===JSON.stringify(currentOriginalRow))throw Error('반영할 변경이 없습니다. 캔버스에서 먼저 드래그하세요.');
  const currentTargets=currentTargetMode==='전체'?currentRows.map((currentRow,currentIndex)=>currentIndex):currentTargetMode==='현재 프레임'?[currentEditorState.index]:(currentSelectedFrames||[]).map(currentNumber=>Number(currentNumber)-1);
  if(!currentTargets.length||currentTargets.some(currentIndex=>!Number.isInteger(currentIndex)||currentIndex<0||currentIndex>=currentRows.length))throw Error('불러온 시트에 있는 프레임을 선택하세요.');
  const currentLeftMargin=currentDraftRow[0]-currentOriginalRow[0],currentTopMargin=currentDraftRow[1]-currentOriginalRow[1];
  const currentRightMargin=currentOriginalRow[2]-currentLeftMargin-currentDraftRow[2],currentBottomMargin=currentOriginalRow[3]-currentTopMargin-currentDraftRow[3];
  const currentUpdatedRows=currentRows.map(currentRow=>[...currentRow]);
  for(const currentIndex of currentTargets){
   const currentTargetRow=currentUpdatedRows[currentIndex];
   currentTargetRow[0]+=currentLeftMargin;currentTargetRow[1]+=currentTopMargin;currentTargetRow[2]-=currentLeftMargin+currentRightMargin;currentTargetRow[3]-=currentTopMargin+currentBottomMargin;
   currentTargetRow[4]+=currentDraftRow[4]-currentOriginalRow[4];currentTargetRow[5]+=currentDraftRow[5]-currentOriginalRow[5];
   if(currentTargetRow[2]<=0||currentTargetRow[3]<=0||currentTargetRow[4]<0||currentTargetRow[5]<0||currentTargetRow[4]>=currentTargetRow[2]||currentTargetRow[5]>=currentTargetRow[3])throw Error(`${currentIndex+1}번 프레임 범위 오류 · 아무 프레임도 변경하지 않았습니다. 크롭 안으로 앵커를 옮기세요.`);
  }
  currentEditorState.undo.push(currentRows);if(currentEditorState.undo.length>30)currentEditorState.undo.shift();
  currentEditorState.expectedSignature=JSON.stringify(currentUpdatedRows);
  return [formatCurrentRows(currentUpdatedRows),`${currentTargets.length}개 프레임 적용 · 에셋에는 아직 저장하지 않았습니다.`];
 }catch(currentApplyError){return [currentFrameRows,currentApplyError.message];}
}
