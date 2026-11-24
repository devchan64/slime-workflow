export function resolveModelSelection(models,current,requested){
  const contains=id=>models.some(model=>model.id===id);
  if(current)return contains(current) ? {selected:current,missing:""} : {selected:"",missing:current};
  if(requested)return contains(requested) ? {selected:requested,missing:""} : {selected:"",missing:requested};
  return {selected:models[0]?.id || "",missing:""};
}
