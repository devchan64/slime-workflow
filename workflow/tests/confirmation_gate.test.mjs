import test from 'node:test';
import assert from 'node:assert/strict';
import {createConfirmationGate} from '../../gui/confirmationGate.mjs';
test('cancelled or consumed confirmation cannot submit; a new review is distinct',()=>{
 const gate=createConfirmationGate(),cancelled=gate.open();gate.cancel();assert.equal(gate.claim(cancelled),false);
 const first=gate.open();assert.equal(gate.claim(first),true);assert.equal(gate.claim(first),false);
 const old=gate.open(),current=gate.open();assert.equal(gate.claim(old),false);assert.equal(gate.claim(current),true);
});
