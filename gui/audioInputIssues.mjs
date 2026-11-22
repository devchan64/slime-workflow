import {generationReady} from './generationReady.mjs';
export function audioInputIssues(form,music,model){
  const issues=[];
  if(music ? !form?.prompt?.split(',').some(tag=>tag.trim()) : !form?.prompt?.trim())issues.push(music?'음악 태그를 입력하세요.':'효과음 설명을 입력하세요.');
  if(music && !form?.lyrics?.trim())issues.push('가사 또는 구간 태그를 입력하세요.');
  if(music && !generationReady(model))issues.push(model?'모델 준비 상태를 확인하고 필요한 준비를 완료하세요.':'모델 준비 상태를 확인하세요.');
  return issues;
}
