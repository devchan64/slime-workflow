import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

const source=readFileSync(new URL('../../gui/BuildingSessionReceipts.jsx',import.meta.url),'utf8');
test('대화 에셋 접수 조회 후 잃은 초점만 결과나 재조회로 복구한다',()=>{
  const start=source.indexOf('  useEffect(()=>{if(busy || !focus.current)'),end=source.indexOf('\n',start);assert.ok(start>=0 && end>start);
  for(const success of [true,false])for(const moved of [true,false]){
    const body={},other={},document={body,activeElement:moved?other:body},focused=[];
    const target=name=>({isConnected:true,disabled:false,focus(){focused.push(name);}});
    const context=vm.createContext({document,restoreLostFocus,busy:false,page:{},error:'',focus:{current:{success}},heading:{current:target('heading')},refresh:{current:target('refresh')},useEffect:fn=>fn()});
    vm.runInContext(source.slice(start,end),context);assert.deepEqual(focused,moved?[]:[success?'heading':'refresh']);assert.equal(context.focus.current,null);
  }
});
