/** 저장 참조 이미지를 이력 입력 미리보기에 전달한다. */
export function kimodoHistoryRequest(saved){
  if(!saved?.inputs || typeof saved.inputs!=='object' || Array.isArray(saved.inputs) || !Array.isArray(saved.references) || saved.references.some(reference=>!reference || typeof reference.data!=='string' || !reference.data))throw Error('저장된 Kimodo 입력을 확인할 수 없습니다.');
  return {...saved.inputs,images:saved.references.map(reference=>reference.data)};
}
