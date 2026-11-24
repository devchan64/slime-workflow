import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('이전 영상 요소의 오류는 현재 미리보기 오류를 바꾸지 않는다',()=>{
 const source=readFileSync(new URL('../../gui/InputVideoPreview.jsx',import.meta.url),'utf8');
 const body=source.split('onError={event=>{')[1].split('}}/>')[0];
 const current={};let failed=null;
 const context=vm.createContext({videoRef:{current},preview:{url:'blob:현재'},setFailedUrl:value=>failed=value});
 vm.runInContext(`function error(event){${body}}`,context);
 context.error({currentTarget:{}});assert.equal(failed,null);
 context.error({currentTarget:current});assert.equal(failed,'blob:현재');
});

test('영상 교체 또는 종료 시 생성한 임시 주소를 해제한다',()=>{
 const source=readFileSync(new URL('../../gui/InputVideoPreview.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{'),source.indexOf('  if(!file || !preview'));
 let cleanup,preview=null,failed='이전';const revoked=[],file={};
 const context=vm.createContext({file,URL:{createObjectURL:value=>{assert.equal(value,file);return 'blob:영상';},revokeObjectURL:url=>revoked.push(url)},
  useEffect:fn=>cleanup=fn(),setPreview:value=>preview=value,setFailedUrl:value=>failed=value});
 vm.runInContext(effect,context);assert.equal(preview.file,file);assert.equal(preview.url,'blob:영상');assert.equal(failed,null);
 cleanup();assert.deepEqual(revoked,['blob:영상']);
 context.file=null;vm.runInContext(effect,context);assert.equal(preview,null);
});
