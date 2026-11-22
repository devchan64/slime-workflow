export async function untilAborted(promise,signal) {
  if(signal.aborted){Promise.resolve(promise).catch(()=>{});throw new DOMException("시간 초과 또는 화면 종료","AbortError");}
  let abort;
  try{return await Promise.race([promise,new Promise((_,reject)=>{abort=()=>reject(new DOMException("시간 초과 또는 화면 종료","AbortError"));signal.addEventListener("abort",abort,{once:true});})]);}
  finally{signal.removeEventListener("abort",abort);}
}

export async function managementCommand(service, command, payload = {}, {signal} = {}) {
  const response = await fetch("/management/command", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({service, command, payload}),
    signal
  });
  if(response.ok && command==="logs" && !response.headers.get("content-type")?.includes("application/json"))
    return {log:await response.text()};
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || value.detail || "요청을 처리할 수 없습니다.");
  return value;
}
