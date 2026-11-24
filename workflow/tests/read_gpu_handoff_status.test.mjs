import test from 'node:test';
import assert from 'node:assert/strict';
import {readGpuHandoffStatus,executeGpuHandoffCommand} from '../../gui/readGpuHandoffStatus.mjs';

test('복구 조회는 요청 범위와 응답 식별자를 확인한다',async()=>{
  const controller=new AbortController(),expected={id:'req',session_id:'session',service:'kimodo',state:'running'};
  const command=async(name,operation,payload,options)=>{
    assert.deepEqual([name,operation,payload],['hermes-agent','hermes-gpu-handoff-status',{session_id:'session',request_id:'req'}]);
    assert.equal(options.signal,controller.signal);return expected;
  };
  assert.equal(await readGpuHandoffStatus(command,'session','req','kimodo',controller.signal),expected);
  await assert.rejects(readGpuHandoffStatus(command,'session','req','other',controller.signal),/일치하지 않습니다/);
});

test('복구 조회가 중단 신호를 무시해도 중단으로 끝난다',async()=>{
  const controller=new AbortController();let resolve;
  const pending=readGpuHandoffStatus(()=>new Promise(done=>{resolve=done;}),'session','req','kimodo',controller.signal);
  controller.abort();await assert.rejects(pending,{name:'AbortError'});
  resolve({id:'req',session_id:'session',service:'kimodo',state:'running'});
});

test('상태 변경 응답이 늦어도 중단 후 결과를 적용하지 않는다',async()=>{
  const controller=new AbortController();let finish;
  const pending=executeGpuHandoffCommand(()=>new Promise(resolve=>{finish=resolve;}),'hermes-gpu-handoff-cancel',{},'session','req','kimodo',controller.signal);
  controller.abort();await assert.rejects(pending,{name:'AbortError'});
  finish({id:'req',session_id:'session',service:'kimodo',state:'cancelled'});
});
