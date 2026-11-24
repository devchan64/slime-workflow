export function initialMotionPlaying(environment=globalThis){
  if(typeof environment.matchMedia!=="function")return true;
  try{return !environment.matchMedia("(prefers-reduced-motion: reduce)").matches;}
  catch{return true;}
}
