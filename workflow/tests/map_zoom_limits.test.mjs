import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('지도 배율 한계는 초점을 유지할 수 있게 설명하고 복귀 시 해제한다',()=>{
 const source=readFileSync(new URL('../../gui/ui/map/block-map-review.js',import.meta.url),'utf8');
 const update=source.slice(source.indexOf('function updateReviewZoomControls(){'),source.indexOf('\nfunction renderSharedReviewMap',source.indexOf('function updateReviewZoomControls(){')));
 const wiring=source.slice(source.indexOf('for(const currentActionName of Object.keys(currentCameraActions))'),source.indexOf('\n// 표준 UI',source.indexOf('for(const currentActionName of Object.keys(currentCameraActions))')));
 assert.ok(update.includes('aria-describedby') && wiring.includes('aria-disabled'));
 for(const existingHelp of [true,false]){
  const nodes=new Map(),calls=[];
  function element(id){const attrs=new Map();return {id,disabled:false,textContent:'',setAttribute:(k,v)=>attrs.set(k,v),removeAttribute:k=>attrs.delete(k),getAttribute:k=>attrs.get(k)??null,after:node=>nodes.set(node.id,node)};}
  for(const id of ['zoom-level','zoom-in','zoom-out'])nodes.set(id,element(id));
  if(existingHelp)for(const id of ['zoom-minimum-help','zoom-maximum-help'])nodes.set(id,element(id));
  const document={querySelector:selector=>nodes.get(selector.slice(1)),getElementById:id=>nodes.get(id),createElement:()=>element('')};
  const context=vm.createContext({document,currentScaleValue:4,MAX_MAP_SCALE:4,MIN_MAP_SCALE:.05,currentCameraActions:{'zoom-in':()=>{},'zoom-out':()=>{}},window:{mapReviewCameraControls:id=>calls.push(id)}});
  vm.runInContext(update+'\n'+wiring+'\nthis.refresh=updateReviewZoomControls;',context);context.refresh();
  const plus=nodes.get('zoom-in'),minus=nodes.get('zoom-out');
  assert.equal(plus.getAttribute('aria-disabled'),'true');assert.equal(plus.disabled,false);assert.equal(plus.getAttribute('aria-describedby'),'zoom-level zoom-maximum-help');
  plus.onclick();assert.equal(calls.length,0);minus.onclick();assert.deepEqual(calls,['zoom-out']);
  context.currentScaleValue=.05;context.refresh();assert.equal(plus.getAttribute('aria-disabled'),null);assert.equal(plus.getAttribute('aria-describedby'),null);
  assert.equal(minus.getAttribute('aria-disabled'),'true');assert.equal(minus.getAttribute('aria-describedby'),'zoom-level zoom-minimum-help');minus.onclick();assert.equal(calls.length,1);
  context.currentScaleValue=.1;context.refresh();assert.equal(minus.getAttribute('aria-disabled'),null);assert.equal(minus.getAttribute('aria-describedby'),null);
  if(!existingHelp){assert.equal(nodes.get('zoom-maximum-help').textContent,'최대 배율입니다.');assert.equal(nodes.get('zoom-minimum-help').textContent,'최소 배율입니다.');}
 }
});
