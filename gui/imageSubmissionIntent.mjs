// Only standalone affirmative instructions may trigger the image submission path.
export function imageSubmissionIntent(value){
  if(typeof value!=="string")return false;
  const text=value.trim().replace(/[.!。！]+$/u,"").trim().replace(/\s+/g,"");
  return /^(?:생성해|생성해줘|생성해주세요|생성해라|생성해보자|생성한다|생성할게|생성하자|생성합니다|GPU양도에동의)$/.test(text);
}
