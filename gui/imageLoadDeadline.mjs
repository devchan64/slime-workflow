export function startImageLoadDeadline(onTimeout,timers=globalThis) {
  let active=true;
  const timer=timers.setTimeout(()=>{if(active){active=false;onTimeout();}},15000);
  return ()=>{active=false;timers.clearTimeout(timer);};
}
