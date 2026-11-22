import test from "node:test";
import assert from "node:assert/strict";
import {matchesLiveInstructionReceipt} from "../../gui/liveInstructionReceipt.mjs";

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

test("uncertain or in-flight receipts cannot confirm a missing local record",()=>{
  const pending={request_id:"request",job_id:"job",mode:"steer",text:"지시"};
  for(const state of ["pending","delivering","unknown"])
    assert.equal(matchesLiveInstructionReceipt({...pending,state},pending,{confirmed:true}),false,state);
  for(const state of ["accepted","applied","undelivered"])
    assert.equal(matchesLiveInstructionReceipt({...pending,state},pending,{confirmed:true}),true,state);
});
