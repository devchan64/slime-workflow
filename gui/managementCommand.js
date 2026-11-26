export async function untilAborted(promise,signal) {
  if(signal.aborted){Promise.resolve(promise).catch(()=>{});throw new DOMException("시간 초과 또는 화면 종료","AbortError");}
  let abort;
  try{return await Promise.race([promise,new Promise((_,reject)=>{abort=()=>reject(new DOMException("시간 초과 또는 화면 종료","AbortError"));signal.addEventListener("abort",abort,{once:true});})]);}
  finally{signal.removeEventListener("abort",abort);}
}

export async function managementCommand(service, command, payload = {}, {signal} = {}) {
  const headers={"Content-Type":"application/json"};
  if(service==="writer-agent" && command.startsWith("writer-") && command!=="writer-state" && command!=="writer-token"){
    const tokenResponse=await fetch("/management/command",{method:"POST",headers,body:JSON.stringify({service,command:"writer-token",payload:{}}),signal});
    let token;
    try{token=await tokenResponse.json();}
    catch(problem){signal?.throwIfAborted();throw new Error("작가 세션을 확인하지 못했습니다. 화면을 다시 열고 시도하세요.");}
    signal?.throwIfAborted();
    if(!tokenResponse.ok || typeof token?.csrf_token!=="string" || !token.csrf_token)throw new Error("작가 세션을 확인하지 못했습니다. 화면을 다시 열고 시도하세요.");
    headers["X-Writer-Token"]=token.csrf_token;
  }
  const response = await fetch("/management/command", {
    method: "POST",
    headers,
    body: JSON.stringify({service, command, payload}),
    signal
  });
  if(response.ok && command==="logs" && !response.headers.get("content-type")?.includes("application/json"))
    return {log:await response.text()};
  let value;
  try{value=await response.json();}
  catch(problem){signal?.throwIfAborted();throw new Error("서버 응답을 확인할 수 없습니다. 다시 시도하세요.");}
  if (!response.ok) {
    const message=[value?.error,value?.detail].find(item=>typeof item==="string" && item.trim());
    throw new Error(message || "요청을 처리할 수 없습니다.");
  }
  return value;
}
