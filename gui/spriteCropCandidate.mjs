export function cropCandidate(image,padding,result){
  if(typeof image!=='string' || !image || !Number.isInteger(padding) || padding<0 || padding>500 || !Array.isArray(result?.frames) || !result.frames.length || !Array.isArray(result.sourceFrames) || result.sourceFrames.length!==result.frames.length)throw new Error('검출 결과를 확인할 수 없습니다.');
  return {image,padding,result};
}
export function confirmCropCandidate(candidate,image,padding){
  if(!candidate || candidate.image!==image || candidate.padding!==Number(padding))throw new Error('시트 또는 여백이 변경되었습니다. 크롭 후보를 다시 검출하세요.');
  return candidate.result;
}
