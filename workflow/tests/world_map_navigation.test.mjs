import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('월드맵 선택은 기존 주소와 이력 상태를 보존한다',()=>{
 const source=readFileSync(new URL('../../gui/WorldMap.jsx',import.meta.url),'utf8');
 const methods=source.slice(source.indexOf('  function mapUrl('),source.indexOf('  return <section className="world-map-review">'));
 const originalState={page:'map'},calls=[];
 const context=vm.createContext({URL,location:{href:'http://localhost/management/frame/world-map/?session=s1&map=old&filter=x#view'},
   history:{state:originalState,replaceState:(...args)=>calls.push(args)},setId:value=>calls.push(value)});
 vm.runInContext(methods,context);
 const link=new URL(context.mapUrl('new'));context.select('new');
 const [state,title,address]=calls[1];
 assert.equal(calls[0],'new');assert.equal(state,originalState);assert.equal(title,'');
 assert.equal(address.href,link.href);assert.equal(link.searchParams.get('map'),'new');
 assert.equal(link.searchParams.get('session'),'s1');assert.equal(link.searchParams.get('filter'),'x');assert.equal(link.hash,'#view');
});
