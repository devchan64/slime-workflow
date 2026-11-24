import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('타일 미리보기는 실패한 이미지를 그리지 않고 복구된 이미지를 그린다',()=>{
  const html=readFileSync(new URL('../../gui/ui/map/tile-review.html',import.meta.url),'utf8');
  const script=html.split('\n').find(line=>line.startsWith('function drawMapPreview'));
  let draws=0;const context={save(){},beginPath(){},moveTo(){},lineTo(){},closePath(){},clip(){},fill(){},restore(){},stroke(){},drawImage(){draws++;}};
  const canvas={getContext:()=>context},image={complete:true,naturalWidth:0};
  const zoom={value:'1',attributes:{},setAttribute(k,v){this.attributes[k]=v;}};
  const elements={'#mapReviewZoom':zoom,'#mapReviewZoomValue':{},'#mapCanvas':canvas,'#mapVariant':{value:'ground'},'#mapImageError':{textContent:''}};
  const data={mapPreview:{columns:1,rows:1,targetCells:[{column:0,row:0}],terrainRows:[['a']],terrainCodes:{a:{color:'#fff'}}}};
  vm.runInNewContext(script+'\ndrawMapPreview()', {tileReviewData:data,tileImageLookup:new Map([['ground',image]]),tileTimedOut:new Set(),document:{querySelector:key=>elements[key]}});
  assert.equal(draws,0);assert.equal(zoom.attributes['aria-valuetext'],'1.0배');assert.match(elements['#mapImageError'].textContent,/불러오지 못했습니다/);image.naturalWidth=32;
  vm.runInNewContext(script+'\ndrawMapPreview()', {tileReviewData:data,tileImageLookup:new Map([['ground',image]]),tileTimedOut:new Set(),document:{querySelector:key=>elements[key]}});
  assert.equal(draws,1);assert.equal(elements['#mapImageError'].textContent,'');
  image.complete=false;vm.runInNewContext(script+'\ndrawMapPreview()', {tileReviewData:data,tileImageLookup:new Map([['ground',image]]),tileTimedOut:new Set(),document:{querySelector:key=>elements[key]}});
  assert.match(elements['#mapImageError'].textContent,/불러오는 중/);assert.equal(draws,1);
  image.complete=true;vm.runInNewContext(script+'\ndrawMapPreview()', {tileReviewData:data,tileImageLookup:new Map([['ground',image]]),tileTimedOut:new Set(['ground']),document:{querySelector:key=>elements[key]}});
  assert.match(elements['#mapImageError'].textContent,/시간이 초과/);assert.equal(draws,1);
});

test('원본 타일 실패 시 반복 미리보기를 숨기고 오류를 표시한다',()=>{
  const html=readFileSync(new URL('../../gui/ui/map/tile-review.html',import.meta.url),'utf8');
  const script=html.split('\n').find(line=>line.startsWith('for(const variantRecord of tileReviewData.variants)'));
  const modes=html.split('\n').find(line=>line.startsWith('const repeatModes='));
  const grid={children:[],append(child){this.children.push(child);}};
  const document={querySelector:()=>grid,createElement:()=>({style:{},children:[],attributes:{},setAttribute(k,v){this.attributes[k]=v;},focus(){this.focused=true;},append(...items){this.children.push(...items);}})},lookup=new Map(),timedOut=new Set(),timers=new Map();let serial=0;
  const setTimeout=callback=>{timers.set(++serial,callback);return serial;},clearTimeout=id=>timers.delete(id);
  vm.runInNewContext(modes+'\n'+script,{tileReviewData:{variants:[{role:'ground',file:'ground.png'}],tileSize:[32,32],tileability:'repeat-x'},tileImageLookup:lookup,tileTimedOut:timedOut,document,URL,setTimeout,clearTimeout,location:{href:'http://localhost/preview'}});
  const [,image,notice,retry,caption,repeat]=grid.children[0].children;
  assert.equal(lookup.get('ground'),image);
  assert.equal(repeat.style.backgroundRepeat,'repeat-x');assert.equal(caption.textContent,'가로 반복 미리보기');
  assert.equal(repeat.hidden,true);image.onload();assert.equal(repeat.hidden,false);
  image.onerror();assert.equal(repeat.hidden,true);assert.equal(retry.hidden,false);assert.match(notice.textContent,/불러오지 못했습니다/);
  document.activeElement=retry;retry.onclick();assert.match(image.src,/retry=/);assert.equal(retry.attributes['aria-disabled'],'true');const url=image.src;retry.onclick();assert.equal(image.src,url);
  timers.get(serial)();assert.equal(timedOut.has('ground'),true);assert.equal(retry.attributes['aria-disabled'],'false');assert.match(notice.textContent,/초과/);
  retry.onclick();image.onload();assert.equal(timedOut.has('ground'),false);assert.equal(repeat.hidden,false);assert.equal(retry.hidden,true);assert.equal(image.focused,true);assert.match(repeat.style.backgroundImage,/retry=/);assert.equal(notice.textContent,'');
});

test('기록된 네 가지 반복 방식이 정확한 CSS 값으로 연결된다',()=>{
  const html=readFileSync(new URL('../../gui/ui/map/tile-review.html',import.meta.url),'utf8');
  const modes=html.split('\n').find(line=>line.startsWith('const repeatModes='));
  const values=vm.runInNewContext(modes+'\nJSON.stringify(repeatModes)');
  const parsed=JSON.parse(values);
  assert.equal(parsed['repeat-x'][0],'repeat-x');assert.equal(parsed['repeat-y'][0],'repeat-y');
  assert.equal(parsed['repeat-both'][0],'repeat');assert.equal(parsed.none[0],'no-repeat');
});

test('높이 미리보기 실패 후 다시 불러오고 초점을 복구한다',()=>{
  const html=readFileSync(new URL('../../gui/ui/map/tile-review.html',import.meta.url),'utf8');
  const script=html.split('\n').find(line=>line.startsWith('if(tileReviewData.preview)'));
  const panel={hidden:true,children:[],append(...items){this.children.push(...items);}},image={focus(){this.focused=true;}};
  const document={querySelector:key=>key==='#heightPanel'?panel:image,createElement:()=>({attributes:{},setAttribute(k,v){this.attributes[k]=v;}})};
  const timers=new Map();let serial=0;const setTimeout=fn=>{timers.set(++serial,fn);return serial;},clearTimeout=id=>timers.delete(id);
  vm.runInNewContext(script,{tileReviewData:{preview:'height.png'},document,URL,setTimeout,clearTimeout,location:{href:'http://localhost/preview'}});
  const [notice,retry]=panel.children;assert.equal(panel.hidden,false);assert.equal(retry.hidden,true);
  image.onerror();assert.equal(retry.hidden,false);assert.match(notice.textContent,/불러오지 못했습니다/);
  document.activeElement=retry;retry.onclick();assert.match(image.src,/retry=/);assert.equal(retry.attributes['aria-disabled'],'true');const url=image.src;retry.onclick();assert.equal(image.src,url);
  timers.get(serial)();assert.match(notice.textContent,/초과/);assert.equal(retry.attributes['aria-disabled'],'false');retry.onclick();image.onload();assert.equal(retry.hidden,true);assert.equal(image.focused,true);assert.equal(notice.textContent,'');
});

test('후보 전환과 카드 재시도는 같은 지도 상태에 반영된다',()=>{
  const html=readFileSync(new URL('../../gui/ui/map/tile-review.html',import.meta.url),'utf8');
  const script=html.split('<script>')[1].split('</script>')[0];
  function element(tag='div'){
    return {tag,children:[],style:{},attributes:{},complete:false,naturalWidth:0,
      set src(value){this._src=value;this.complete=false;this.naturalWidth=0;},get src(){return this._src;},
      append(...items){this.children.push(...items);if(this.tag==='select' && !this.value)this.value=items[0].value;},
      setAttribute(k,v){this.attributes[k]=v;},addEventListener(type,fn){(this.listeners??={})[type]=fn;},focus(){},
      fire(type){this.complete=true;this.naturalWidth=type==='load'?32:0;this['on'+type]?.();this.listeners?.[type]?.();}};
  }
  const names=['title','summary','tileGrid','heightPanel','heightPreview','warnings','mapPanel','mapTitle','mapVariant','mapReviewZoom','mapReviewZoomValue','mapImageError','mapCanvas'];
  const elements=Object.fromEntries(names.map(name=>['#'+name,element(name==='mapVariant'?'select':'div')]));
  elements['#mapReviewZoom'].value='1';let draws=0;
  elements['#mapCanvas'].getContext=()=>({save(){},beginPath(){},moveTo(){},lineTo(){},closePath(){},clip(){},fill(){},restore(){},stroke(){},drawImage(){draws++;}});
  const document={querySelector:key=>elements[key],createElement:tag=>element(tag)};
  const data={assetId:'test',tileSize:[32,32],tileability:'repeat-both',heightSteps:1,preview:null,qualityWarnings:[],variants:[{role:'ground',file:'ground.png'},{role:'wall-front',file:'wall.png'}],mapPreview:{displayNameKo:'필드',columns:1,rows:1,targetCells:[{column:0,row:0}],terrainRows:[['g']],terrainCodes:{g:{color:'#fff'}}}};
  const timers=new Map();let serial=0;const setTimeout=fn=>{timers.set(++serial,fn);return serial;},clearTimeout=id=>timers.delete(id);
  vm.runInNewContext(script.replace('__TILE_REVIEW_DATA__',JSON.stringify(data)),{document,URL,setTimeout,clearTimeout,location:{href:'http://localhost/preview'}});
  const [groundCard,wallCard]=elements['#tileGrid'].children;const ground=groundCard.children[1],wall=wallCard.children[1],retry=groundCard.children[3],select=elements['#mapVariant'];
  ground.fire('error');assert.match(elements['#mapImageError'].textContent,/ground/);assert.equal(draws,0);
  wall.fire('load');select.value='wall-front';select.onchange();assert.equal(elements['#mapImageError'].textContent,'');assert.equal(draws,1);
  select.value='ground';select.onchange();assert.match(elements['#mapImageError'].textContent,/ground/);
  retry.onclick();assert.match(elements['#mapImageError'].textContent,/불러오는 중/);ground.fire('load');assert.equal(elements['#mapImageError'].textContent,'');assert.equal(draws,2);
});
