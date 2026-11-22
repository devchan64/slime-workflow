import test from 'node:test';
import assert from 'node:assert/strict';
import {fluxModelReady} from '../../gui/fluxModelReady.mjs';
import {generationReady} from '../../gui/generationReady.mjs';

test('generation readiness takes precedence and missing status is unavailable', () => {
  assert.equal(fluxModelReady(null), false);
  assert.equal(fluxModelReady({}), false);
  assert.equal(fluxModelReady({ready:true}), true);
  assert.equal(fluxModelReady({ready:false,generation_ready:true}), true);
  assert.equal(fluxModelReady({ready:true,generation_ready:false}), false);
});

 test('translation also requires its runtime when reported',()=>{
  assert.equal(generationReady({ready:true,generation_ready:false}),false);
  assert.equal(generationReady({ready:true,generation_ready:true}),true);
});
