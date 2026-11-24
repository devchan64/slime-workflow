import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {kimodoPromptReason} from '../../gui/kimodoPromptReason.mjs';

test('Kimodo 동작 설명 오류는 서버 조회 전에 검토를 중단한다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoGeneration.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function inspect()'),source.indexOf('  async function submit()',source.indexOf('  async function inspect()')));
 for(const prompt of ['',Array(101).fill('walk').join(' '),'!!!']){
  let calls=0;const context=vm.createContext({checkingSlots:{current:new Set()},promptReason:kimodoPromptReason(prompt),verifyKimodoProposal:()=>calls++,managementCommand:()=>calls++,setReview:()=>calls++,setHandoffReview:()=>calls++});
  vm.runInContext(code,context);await assert.rejects(context.inspect(),error=>error.message===kimodoPromptReason(prompt));assert.equal(calls,0);
 }
});
