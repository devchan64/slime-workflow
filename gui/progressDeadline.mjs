export function progressDeadline(target, eventName, onTimeout, delay=30000) {
  let timer;
  const renew=()=>{clearTimeout(timer);timer=setTimeout(onTimeout,delay);};
  target.addEventListener(eventName,renew);
  renew();
  return ()=>{target.removeEventListener(eventName,renew);clearTimeout(timer);};
}
