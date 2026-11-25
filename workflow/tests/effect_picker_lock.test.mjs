import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('이펙트 목록 갱신 직후 렌더 전 중복 갱신과 상세 조회를 막는다',async()=>{
  const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
  const start=source.indexOf('onClick={()=>{if(listPending.current');
  const end=source.indexOf('}}>목록 새로고침',start);
  const handler=source.slice(start+'onClick={'.length,end+1);
  const load=source.slice(source.indexOf('  async function load(){',source.indexOf('export default function EffectEditor')),source.indexOf('  const choices=',source.indexOf('export default function EffectEditor')));
  let refreshes=0,requests=0;
  const context=vm.createContext({listPending:{current:false},detailRequest:{current:null},busy:false,editorBusy:false,dirty:false,effects:[{id:'a'}],selected:'a',
    document:{activeElement:null},reloadRef:{current:null},restorePickerFocus:{current:''},setBusy:()=>{},reload:()=>refreshes++,managementCommand:()=>requests++});
  vm.runInContext(load+';globalThis.refresh='+handler,context);
  context.refresh();context.refresh();await context.load();
  assert.equal(refreshes,1);assert.equal(requests,0);
});
