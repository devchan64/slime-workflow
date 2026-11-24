export function handoffUncertaintyKey(session,id,service){
  return 'gpu-handoff-uncertain:v1:'+JSON.stringify([session,id,service]);
}

export function handoffSessionStorage(){
  try{return globalThis.sessionStorage;}catch{return null;}
}

export function readHandoffUncertainty(storage,key){
  try{return {uncertain:storage.getItem(key)!==null,available:true};}
  catch{return {uncertain:true,available:false};}
}

export function markHandoffUncertainty(storage,key){
  try{storage.setItem(key,'pending');return true;}catch{return false;}
}

export function clearHandoffUncertainty(storage,key){
  try{storage.removeItem(key);return true;}catch{return false;}
}
