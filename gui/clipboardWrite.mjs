export async function writeClipboardText(value,timeoutMs=5000) {
  if (!navigator.clipboard?.writeText) throw new Error("클립보드를 사용할 수 없습니다.");
  let timer;
  try {
    return await Promise.race([navigator.clipboard.writeText(value),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error("클립보드 응답 시간 초과")),timeoutMs);})]);
  } finally {clearTimeout(timer);}
}
