import {countPromptWords} from './promptWords.mjs';

export function kimodoPromptReason(prompt){
  if(typeof prompt!=='string' || !prompt.trim())return '동작 설명을 입력한 뒤 요청을 검토하세요.';
  if(countPromptWords(prompt)>100)return '동작 설명은 100단어 이내로 줄여 주세요.';
  if(!/[\p{L}\p{N}]/u.test(prompt))return '동작 설명에 문자 또는 숫자를 입력하세요.';
  return '';
}
