export function cropCandidate(image,padding,result,size){
  const integer=Number.isInteger;
  if(typeof image!=='string' || !image || !integer(padding) || padding<0 || padding>500 || !Array.isArray(result?.frames) || !result.frames.length || result.frames.length>128 || !Array.isArray(result.sourceFrames) || result.sourceFrames.length!==result.frames.length || !integer(result.columns) || result.columns<1 || !integer(result.rows) || result.rows<1 || result.columns*result.rows!==result.frames.length || result.padding!==padding)throw new Error('검출 결과를 확인할 수 없습니다.');
  if(result.frames.some(frame=>!frame || !['x','y','width','height'].every(key=>integer(frame[key])) || frame.width<1 || frame.height<1 || !Number.isFinite(frame.anchorX) || !Number.isFinite(frame.anchorY)) || result.sourceFrames.some(rect=>!Array.isArray(rect) || rect.length!==4 || !rect.every(integer) || rect[0]<0 || rect[1]<0 || rect[2]<1 || rect[3]<1 || (size && (rect[0]+rect[2]>size.width || rect[1]+rect[3]>size.height))))throw new Error('검출 결과를 확인할 수 없습니다.');
  return {image,padding,result};
}
export function confirmCropCandidate(candidate,image,padding){
  if(!candidate || candidate.image!==image || candidate.padding!==Number(padding))throw new Error('시트 또는 여백이 변경되었습니다. 크롭 후보를 다시 검출하세요.');
  return candidate.result;
}
