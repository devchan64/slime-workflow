export function imageRetryUrl(src,revision){
  if(/^(data|blob):/i.test(src))return src;
  const hashIndex=src.indexOf("#"),base=hashIndex<0 ? src : src.slice(0,hashIndex),fragment=hashIndex<0 ? "" : src.slice(hashIndex);
  return base+(base.includes("?") ? "&" : "?")+"retry="+revision+fragment;
}
