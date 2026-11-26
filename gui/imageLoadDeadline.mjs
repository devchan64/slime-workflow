export function startImageLoadDeadline(onTimeout,timers=globalThis) {
  let active=true;
  const timer=timers.setTimeout(()=>{if(active){active=false;onTimeout();}},15000);
  return ()=>{active=false;timers.clearTimeout(timer);};
}

export function startVisibleImageLoadDeadline(element,onTimeout,{Observer=globalThis.IntersectionObserver,timers=globalThis}={}) {
  if(!element || !Observer)return ()=>{};
  let active=true,started=false,cancelDeadline=null;
  const observer=new Observer(entries=>{
    if(!active || started || !entries.some(entry=>entry.isIntersecting))return;
    started=true;
    observer.disconnect();
    cancelDeadline=startImageLoadDeadline(()=>{if(active){active=false;onTimeout();}},timers);
  });
  observer.observe(element);
  return ()=>{active=false;observer.disconnect();cancelDeadline?.();};
}
