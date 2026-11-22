export function latestRequest() {
  let revision=0;
  return {
    start:()=>++revision,
    invalidate:()=>{revision++;},
    isCurrent:token=>token===revision,
  };
}
