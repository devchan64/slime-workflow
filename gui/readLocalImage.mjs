export function readLocalImageBase64(file,{Reader=globalThis.FileReader,timers=globalThis,signal}={}) {
  return new Promise((resolve,reject)=>{
    if(signal?.aborted){reject(new DOMException("이미지 읽기가 중단됐습니다.","AbortError"));return;}
    const reader=new Reader();let finished=false;
    const finish=(error,value)=>{
      if(finished)return;finished=true;timers.clearTimeout(timer);
      signal?.removeEventListener("abort",abort);
      reader.onload=null;reader.onerror=null;reader.onabort=null;
      if(error)reject(error);else resolve(value);
    };
    const abort=()=>{finish(new DOMException("이미지 읽기가 중단됐습니다.","AbortError"));try{reader.abort();}catch{}};
    const timer=timers.setTimeout(()=>{
      finish(new Error("이미지 읽기 시간이 초과됐습니다. 파일을 다시 선택하세요."));
      try{reader.abort();}catch{}
    },30000);
    reader.onload=()=>{
      const result=reader.result;
      if(typeof result!=="string" || !result.includes(",")){finish(new Error("이미지를 읽을 수 없습니다."));return;}
      finish(null,result.slice(result.indexOf(",")+1));
    };
    reader.onerror=()=>finish(new Error("이미지를 읽을 수 없습니다."));
    reader.onabort=()=>finish(new Error("이미지 읽기가 중단됐습니다."));
    signal?.addEventListener("abort",abort,{once:true});
    try{reader.readAsDataURL(file);}catch{finish(new Error("이미지를 읽을 수 없습니다."));}
  });
}
