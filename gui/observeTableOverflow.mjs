export function observeTableOverflow(container,table,onChange,{window,Observer}) {
  let active=true;
  const update=()=>{if(active)onChange(container.scrollWidth>container.clientWidth+1);};
  update();
  const observer=typeof Observer==="function" ? new Observer(update) : null;
  observer?.observe(container);
  if(table)observer?.observe(table);
  window.addEventListener("resize",update);
  container.addEventListener("load",update,true);
  const fonts=container.ownerDocument?.fonts;
  fonts?.addEventListener?.("loadingdone",update);
  return ()=>{active=false;observer?.disconnect();window.removeEventListener("resize",update);container.removeEventListener("load",update,true);fonts?.removeEventListener?.("loadingdone",update);};
}

export function scrollTableOnArrow(event) {
  const node=event.currentTarget;
  if(event.target!==node || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || node.scrollWidth<=node.clientWidth+1 || !["ArrowLeft","ArrowRight"].includes(event.key))return;
  event.preventDefault();
  node.scrollLeft+=event.key==="ArrowRight" ? 80 : -80;
}
