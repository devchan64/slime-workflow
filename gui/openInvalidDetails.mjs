export function openInvalidDetails(event,details,schedule=requestAnimationFrame){
  const target=event.target;
  if(!details || details.open || !details.contains(target) || event.currentTarget.querySelector('input:invalid,select:invalid,textarea:invalid')!==target)return;
  const doc=target.ownerDocument,origin=doc?.activeElement;
  details.open=true;
  schedule(()=>{if(target.isConnected && (!doc || doc.activeElement===origin || doc.activeElement===doc.body || doc.activeElement===target))target.focus();});
}
