import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('기존 이력 조회 인자는 유지하고 신호 지원 조회에만 신호를 전달한다',async()=>{
  const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
  const method='async function read(id) {'+source.split('async function read(id) {')[1].split('\n  async function showResult',1)[0];
  const scope={service:'service',resultId:'',externalResultId:''};let mode='';
  const context=vm.createContext({AbortController,setTimeout:()=>1,clearTimeout:()=>{},untilAborted:promise=>promise,
    inputScope:{current:scope},inputRequest:{current:null},service:'service',statusCommand:'status',
    readJob:async(...args)=>{assert.equal(args.length,1);mode='legacy';return {id:args[0],request:{}};},readJobWithSignal:null});
  vm.runInContext(method,context);assert.equal((await context.read('job')).id,'job');assert.equal(mode,'legacy');
  context.readJobWithSignal=async(id,options)=>{assert.ok(options.signal instanceof AbortSignal);mode='signal';return {id,request:{}};};
  assert.equal((await context.read('job')).id,'job');assert.equal(mode,'signal');
});

test('취소 후 늦게 끝난 이력 입력은 반환하지 않는다',async()=>{
  const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
  const read='async function read(id) {'+source.split('async function read(id) {')[1].split('\n  async function showResult',1)[0];
  const cancel='function cancelInput(){'+source.split('function cancelInput(){')[1].split('\n  function cancelList',1)[0];
  const scope={service:'service',resultId:'',externalResultId:''};let resolveLate,receivedSignal;
  const context=vm.createContext({AbortController,setTimeout:()=>1,clearTimeout:()=>{},untilAborted,
    inputScope:{current:scope},inputRequest:{current:null},service:'service',statusCommand:'status',readJob:null,
    readJobWithSignal:(_id,{signal})=>{receivedSignal=signal;return new Promise(resolve=>resolveLate=resolve);}});
  vm.runInContext(cancel+'\n'+read,context);
  const pending=context.read('job');context.cancelInput();assert.equal(receivedSignal.aborted,true);
  assert.equal(await pending,null);resolveLate({id:'job',request:{}});await Promise.resolve();assert.equal(context.inputRequest.current,null);
});
