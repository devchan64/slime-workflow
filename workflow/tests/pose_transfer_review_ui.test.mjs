import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('포즈 비교 프레임 버튼은 경로를 이미지 속성으로 사용하고 선택을 표시한다',()=>{
  const html=readFileSync(new URL('../../gui/ui/asset_review/pose-transfer-review.html',import.meta.url),'utf8');
  const script=html.split('<script>')[1].split('</script>')[0];
  function element(){return {children:[],style:{},attributes:{},panel:{},closest(){return this.panel;},getAttribute(k){return this[k]??null;},removeAttribute(k){delete this[k];},append(...items){this.children.push(...items);},prepend(...items){this.children.unshift(...items);},after(...items){this.following=items;},focus(){this.focused=true;},setAttribute(k,v){this.attributes[k]=v;},set innerHTML(value){if(value==='')this.children=[];else throw Error('unexpected HTML');}};}
  const names=['directionChoice','reportLabel','resultImage','rigImage','openposeImage','overlayToggle','overlayOpacity','overlayStatus','frameLabel','frameDetails','frameStrip','previous','next'];
  const elements=Object.fromEntries(names.map(name=>['#'+name,element()]));
  elements['#resultImage'].alt='결과';elements['#rigImage'].alt='리그';elements['#openposeImage'].alt='OpenPose';
  elements['#resultImage'].parentElement=element();
  elements['#resultImage'].panel=element();
  elements['#overlayOpacity'].value='45';
  const document={querySelector:key=>elements[key],querySelectorAll:()=>elements['#frameStrip'].children,createElement:()=>element(),createTextNode:value=>value};
  const path='frame-01/<unsafe>".png';
  const frames=Array.from({length:8},(_,index)=>({frame:index+1,size:[256,256],modelRevision:'v',files:{result:{path},rig:{path:'rig.png'},openpose:{path:'pose.png'}}}));
  frames[3].files.result.path='frame-04/new.png';
  const data={report:'fixture',directions:[{direction:'down_left',frames}]};
  const timers=new Map();let timerId=0;const setTimeout=fn=>{const id=++timerId;timers.set(id,fn);return id;},clearTimeout=id=>timers.delete(id);
  vm.runInNewContext(script.replace('__POSE_TRANSFER_DATA__',JSON.stringify(data)),{document,URL,setTimeout,clearTimeout,location:{href:'http://localhost/preview'}});
  const buttons=elements['#frameStrip'].children;
  const overlay=elements['#resultImage'].parentElement.children[0];assert.equal(overlay.hidden,true);
  elements['#overlayToggle'].checked=true;elements['#overlayToggle'].oninput();assert.equal(overlay.hidden,true);assert.equal(elements['#resultImage'].style.opacity,1);assert.match(elements['#overlayStatus'].textContent,/참조 이미지/);
  const rig=elements['#rigImage'],rigRetry=rig.following[1],overlayRetry=elements['#resultImage'].panel.children[1];
  assert.equal(rigRetry.attributes['aria-label'],'리그 이미지 다시 불러오기');
  rig.onerror();assert.equal(rigRetry.hidden,false);rigRetry.onclick();rig.onload();assert.equal(overlay.hidden,true);assert.match(overlay.src,/retry=/);assert.match(elements['#overlayStatus'].textContent,/불러오는 중/);
  overlay.onerror();assert.equal(overlay.hidden,true);assert.equal(overlayRetry.hidden,false);assert.equal(elements['#resultImage'].style.opacity,1);assert.match(elements['#overlayStatus'].textContent,/다시 불러오세요/);
  document.activeElement=overlayRetry;overlayRetry.onclick();assert.match(overlay.src,/overlayRetry=/);assert.equal(overlayRetry.hidden,false);assert.equal(overlayRetry.attributes['aria-disabled'],'true');const overlayRetryUrl=overlay.src;overlayRetry.onclick();assert.equal(overlay.src,overlayRetryUrl);
  const staleLoad=overlay.onload,timeout=timers.get(timerId);timeout();staleLoad();assert.equal(overlayRetry.hidden,false);assert.equal(overlayRetry.attributes['aria-disabled'],'false');assert.equal(overlay.hidden,true);
  overlayRetry.onclick();overlay.onload();assert.equal(overlay.hidden,false);assert.equal(overlayRetry.hidden,true);assert.equal(elements['#resultImage'].focused,true);
  assert.equal(overlay.src.includes('overlayRetry='),true);
  elements['#overlayToggle'].checked=false;elements['#overlayToggle'].oninput();assert.equal(overlay.hidden,true);
  assert.equal(buttons.length,8);assert.equal(buttons[0].children[0].src,path);
  assert.equal(buttons[0].attributes['aria-label'],'1번 프레임');assert.equal(buttons[0].attributes['aria-pressed'],'true');
  buttons[0].children[0].onerror();assert.equal(buttons[0].children[0].hidden,true);assert.match(buttons[0].attributes['aria-label'],/미리보기 없음/);assert.equal(buttons[0].children[2].textContent,'미리보기 없음');
  buttons[2].onclick();assert.equal(buttons[2].attributes['aria-pressed'],'true');assert.equal(elements['#frameLabel'].textContent,'3 / 8 프레임');
  const image=elements['#resultImage'],[notice,retry]=image.following;image.alt='결과';image.onerror();
  assert.match(notice.textContent,/불러오지 못했습니다/);assert.equal(retry.hidden,false);
  retry.onclick();assert.match(image.src,/retry=/);const retryUrl=image.src;elements['#overlayToggle'].oninput();assert.equal(image.src,retryUrl);
  document.activeElement=retry;image.onload();
  assert.equal(retry.hidden,true);assert.equal(notice.textContent,'');assert.equal(image.focused,true);
  const previousLoad=image.onload;buttons[3].onclick();previousLoad();assert.equal(notice.textContent,'');assert.equal(retry.hidden,true);assert.equal(image.src,'frame-04/new.png');
  for(const frame of frames){delete frame.files.openpose;delete frame.modelRevision;}
  vm.runInNewContext(script.replace('__POSE_TRANSFER_DATA__',JSON.stringify(data)),{document,URL,setTimeout,clearTimeout,location:{href:'http://localhost/preview'}});
  assert.equal(elements['#openposeImage'].panel.hidden,true);assert.equal(elements['#rigImage'].panel.hidden,false);
  assert.match(elements['#frameDetails'].textContent,/모델 정보 없음/);
});
