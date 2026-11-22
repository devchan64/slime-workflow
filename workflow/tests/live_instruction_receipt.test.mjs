import test from "node:test";
import assert from "node:assert/strict";
import {matchesLiveInstructionReceipt,matchesLiveInstructionRecovery,validLiveInstructionRows} from "../../gui/liveInstructionReceipt.mjs";
import {createHash} from "node:crypto";

test("receipt must identify the same job, request, instruction and mode",()=>{
  const pending={request_id:"request",job_id:"job",mode:"steer",text:"지시"};
  const receipt={...pending,state:"accepted"};
  assert.equal(matchesLiveInstructionReceipt(receipt,pending),true);
  for(const [field,value] of Object.entries({request_id:"other",job_id:"other",mode:"redirect",text:"다른 지시",state:"invalid"}))
    assert.equal(matchesLiveInstructionReceipt({...receipt,[field]:value},pending),false,field);
  assert.equal(matchesLiveInstructionReceipt({request_id:"request",state:"accepted"},pending),false);
  assert.equal(matchesLiveInstructionReceipt({state:"accepted"},{}, {confirmed:true}),false);
  assert.equal(matchesLiveInstructionReceipt({...receipt,text:""},{...pending,text:""}),false);
});

test("복구 응답은 원래 지시의 결정적 복구 ID와 일치해야 한다",async()=>{
  const receipt={request_id:"receipt01",text:"같은 지시"};
  const id="recovery_"+createHash("sha256").update(receipt.request_id).digest("hex");
  const response={duplicate:false,request:{request_id:id,original_prompt:receipt.text,state:"queued"}};
  assert.equal(await matchesLiveInstructionRecovery(response,receipt),true);
  assert.equal(await matchesLiveInstructionRecovery({...response,request:{...response.request,request_id:"recovery_other"}},receipt),false);
  assert.equal(await matchesLiveInstructionRecovery({...response,request:{...response.request,original_prompt:"다른 지시"}},receipt),false);
  assert.equal(await matchesLiveInstructionRecovery({...response,duplicate:"false"},receipt),false);
  assert.equal(await matchesLiveInstructionRecovery({...response,request:{...response.request,state:"invalid"}},receipt),false);
  assert.equal(await matchesLiveInstructionRecovery({...response,duplicate:true,request:{...response.request,state:"cancelled"}},receipt),true);
});

test("uncertain or in-flight receipts cannot confirm a missing local record",()=>{
  const pending={request_id:"request",job_id:"job",mode:"steer",text:"지시"};
  for(const state of ["pending","delivering","unknown"])
    assert.equal(matchesLiveInstructionReceipt({...pending,state},pending,{confirmed:true}),false,state);
  for(const state of ["accepted","applied","undelivered"])
    assert.equal(matchesLiveInstructionReceipt({...pending,state},pending,{confirmed:true}),true,state);
});

test("지시 내역의 중복 ID와 불완전한 항목을 거부한다",()=>{
  const row={request_id:"receipt01",job_id:"job01",text:"지시",state:"undelivered",mode:"steer"};
  assert.equal(validLiveInstructionRows([row]),true);
  assert.equal(validLiveInstructionRows([row,row]),false);
  assert.equal(validLiveInstructionRows([{...row,mode:"other"}]),false);
  assert.equal(validLiveInstructionRows([{...row,job_id:""}]),false);
  assert.equal(validLiveInstructionRows([{...row,state:"invalid"}]),false);
});
