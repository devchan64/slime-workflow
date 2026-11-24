export function observeLiveVisibility(element,onChange,{document,window,Observer}) {
  let intersecting=false,active=true,observer;
  const update=()=>{if(active)onChange(intersecting && document.visibilityState==="visible");};
  const updateFromBounds=()=>{
    const bounds=element.getBoundingClientRect();
    let left=Math.max(0,bounds.left),right=Math.min(window.innerWidth,bounds.right);
    let top=Math.max(0,bounds.top),bottom=Math.min(window.innerHeight,bounds.bottom);
    for(let parent=element.parentElement;parent && right>left && bottom>top;parent=parent.parentElement){
      const style=window.getComputedStyle(parent),clip=parent.getBoundingClientRect();
      if(["auto","scroll","hidden","clip"].includes(style.overflowX)){left=Math.max(left,clip.left);right=Math.min(right,clip.right);}
      if(["auto","scroll","hidden","clip"].includes(style.overflowY)){top=Math.max(top,clip.top);bottom=Math.min(bottom,clip.bottom);}
    }
    intersecting=right>left && bottom>top;
    update();
  };
  if(typeof Observer==="function"){
    observer=new Observer(entries=>{intersecting=entries[0]?.isIntersecting || false;update();});
    observer.observe(element);
  } else {
    window.addEventListener("scroll",updateFromBounds,true);
    window.addEventListener("resize",updateFromBounds);
    updateFromBounds();
  }
  const onVisibilityChange=()=>{if(observer)update();else updateFromBounds();};
  document.addEventListener("visibilitychange",onVisibilityChange);
  return ()=>{
    active=false;observer?.disconnect();
    window.removeEventListener("scroll",updateFromBounds,true);
    window.removeEventListener("resize",updateFromBounds);
    document.removeEventListener("visibilitychange",onVisibilityChange);
  };
}
