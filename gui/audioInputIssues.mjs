import {generationReady} from './generationReady.mjs';
export function audioSeedValid(value){return value!=='' && value!=null && Number.isInteger(Number(value)) && Number(value)>=0 && Number(value)<=4294967295;}
export function audioDurationValid(value){return value!=='' && value!=null && Number.isFinite(Number(value)) && Number(value)>=5 && Number(value)<=300;}
export function audioInputIssues(form,music,model){
  const issues=[];
  if(music ? !form?.prompt?.split(',').some(tag=>tag.trim()) : !form?.prompt?.trim())issues.push(music?'음악 태그를 입력하세요.':'효과음 설명을 입력하세요.');
  if(music && !form?.lyrics?.trim())issues.push('가사 또는 구간 태그를 입력하세요.');
  if(!audioSeedValid(form?.seed))issues.push('시드는 0부터 4,294,967,295까지의 정수로 입력하세요.');
  if(music && !audioDurationValid(form?.duration_seconds))issues.push('최대 출력 시간은 5~300초로 입력하세요.');
  if(music && !generationReady(model))issues.push(model?'모델 준비 상태를 확인하고 필요한 준비를 완료하세요.':'모델 준비 상태를 확인하세요.');
  return issues;
}
