export function parseTranslationGlossary(text){
  const seen=new Set();
  const lines=text.split(/\r?\n/).filter(line=>line.trim());
  if(lines.length>50)throw new Error('용어는 최대 50개까지 지정할 수 있습니다.');
  return lines.map(line=>{
    const pair=line.split('=>').map(term=>term.trim());
    if(pair.length!==2 || pair.some(term=>!term))throw new Error('용어는 한 줄에 원문 => 번역어로 입력하세요.');
    if(pair.some(term=>Array.from(term).length>100 || /[\r\n]/.test(term)))throw new Error('용어 원문과 번역어는 한 줄의 1~100자여야 합니다.');
    if(seen.has(pair[0]))throw new Error('같은 원문 용어를 중복해서 입력할 수 없습니다: '+pair[0]);
    seen.add(pair[0]);
    return {source:pair[0],target:pair[1]};
  });
}
