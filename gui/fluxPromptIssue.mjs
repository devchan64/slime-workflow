export function fluxPromptIssue(form, service) {
  if (service === 'flux-building' || service === 'flux-expression') return '';
  return form.translation_source_ko?.trim() && /[가-힣]/.test(form.prompt || '')
    ? '번역할 한국어 설명을 함께 쓰려면 프롬프트에서 한국어를 지우거나 영어로 바꾸세요.'
    : '';
}

export function fluxTranslationIssue(form, service) {
  if (service === 'flux-building') return '';
  const source = (form.translation_source_ko || '').trim();
  if (!source) return '';
  return Array.from(source).length > 6000 || !/[가-힣]/.test(source)
    ? '번역할 설명을 6,000자 이하의 한국어로 입력하세요.'
    : '';
}
