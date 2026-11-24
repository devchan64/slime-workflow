export function observeTableOverflow(container,table,onChange,{window,Observer}) {
  let active=true;
  const update=()=>{if(active)onChange(container.scrollWidth>container.clientWidth+1);};
  update();
  const observer=typeof Observer==="function" ? new Observer(update) : null;
  observer?.observe(container);
  if(table)observer?.observe(table);
  window.addEventListener("resize",update);
  return ()=>{active=false;observer?.disconnect();window.removeEventListener("resize",update);};
}
