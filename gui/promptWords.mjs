export function countPromptWords(text) {
  if (typeof text !== 'string' || !text.trim()) return 0;
  return text.trim().split(/\s+/u).length;
}
