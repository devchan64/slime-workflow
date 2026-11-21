export function referenceImageError(file,accept,maxBytes) {
  if (!file?.type?.startsWith('image/')) return '이미지 파일을 선택하세요.';
  if (accept==='image/png' && file.type!=='image/png') return 'PNG 이미지 파일을 선택하세요.';
  if (maxBytes!==null && file.size>maxBytes) return '이미지 파일은 '+(maxBytes/1000000)+'MB 이하여야 합니다.';
  return '';
}
