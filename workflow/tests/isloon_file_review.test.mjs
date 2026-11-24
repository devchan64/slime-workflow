import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {test} from 'node:test';

test('맵 파일 오류는 정상 미리보기를 유지하고 늦은 파일은 덮어쓰지 않는다',async()=>{
 const html=readFileSync(new URL('../../gui/ui/map/isloon-map-review.html',import.meta.url),'utf8');
 const context={clearRect(){},fillRect(){},beginPath(){},moveTo(){},lineTo(){},stroke(){}};
 const nodes={'#map':{width:768,height:576,getContext:()=>context},'#map-file':{},'#summary':{},'#map-error':{}};
 vm.runInNewContext(html.split('<script type="module">')[1].split('</script>')[0],{document:{querySelector:key=>nodes[key]}});
 const change=nodes['#map-file'].onchange;
 const map=id=>JSON.stringify({map_id:id,grid:{columns:2,rows:2},layers:{ground:[]},spawn:{column:0,row:0}});
 await change({target:{files:[{name:'map.json',text:async()=>map('정상')}]}});
 assert.match(nodes['#summary'].textContent,/정상/);
 assert.match(nodes['#summary'].textContent,/map\.json/);
 await change({target:{files:[{text:async()=>'{'}]}});
 assert.match(nodes['#map-error'].textContent,/다시 선택/);
 assert.match(nodes['#summary'].textContent,/정상/);
 assert.match(nodes['#summary'].textContent,/map\.json/);
 const invalidTarget={files:[{text:async()=>JSON.stringify({grid:{columns:0,rows:2}})}],value:'broken.json'};
 await change({target:invalidTarget});
 assert.equal(invalidTarget.value,'');
 assert.match(nodes['#map-error'].textContent,/격자/);
 assert.match(nodes['#summary'].textContent,/정상/);
 let resolve;const old=change({target:{files:[{text:()=>new Promise(r=>{resolve=r;})}]}});
 await change({target:{files:[{text:async()=>map('최신')}]}});resolve(map('이전'));await old;
 assert.match(nodes['#summary'].textContent,/최신/);
 assert.equal(nodes['#map-error'].textContent,'');
});
