import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('앵커 이력 조회·검토·취소 후 잃은 초점만 지정된 위치로 복구한다',()=>{
  const source=readFileSync(new URL('../../gui/SpriteAnchorRestore.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{if(busy || !focusPending.current)'),end=source.indexOf('\n',start);assert.ok(start>=0 && end>start);
  for(const targetName of ['select','review','prepare','notice','trigger'])for(const moved of [false,true]){
    const body={},other={},document={body,activeElement:moved?other:body},focused=[];
    const target=name=>({isConnected:true,disabled:false,focus(){focused.push(name);}});
    const context=vm.createContext({document,restoreLostFocus,busy:false,review:null,notice:'',focusPending:{current:{target:targetName,trigger:target('trigger')}},selectRef:{current:target('select')},reviewRef:{current:target('review')},expiredRef:{current:target('expired')},prepareRef:{current:target('prepare')},noticeRef:{current:target('notice')},useEffect:fn=>fn()});
    vm.runInContext(source.slice(start,end),context);assert.deepEqual(focused,moved?[]:[targetName]);assert.equal(context.focusPending.current,null);
  }
});
test('앵커 복원 검토가 만료되면 잃은 초점을 만료 안내로 복구한다',()=>{
  const source=readFileSync(new URL('../../gui/SpriteAnchorRestore.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{if(busy || !focusPending.current)'),end=source.indexOf('\n',start),body={},document={body,activeElement:body};let focused=false;
  const context=vm.createContext({document,restoreLostFocus,busy:false,review:{},notice:'',focusPending:{current:{target:'review'}},selectRef:{current:null},reviewRef:{current:null},expiredRef:{current:{isConnected:true,disabled:false,focus(){focused=true;}}},prepareRef:{current:null},noticeRef:{current:null},useEffect:fn=>fn()});
  vm.runInContext(source.slice(start,end),context);assert.equal(focused,true);
});
