import assert from 'node:assert/strict';
import {generatorPageIdentity, generatorPages} from '../../gui/generatorPageRegistry.mjs';
assert.equal(generatorPageIdentity('kimodo').changelog, 'kimodo-generator');
assert.equal(generatorPageIdentity('wan22-vace').changelog, 'wan22-vace-generator');
assert.equal(generatorPageIdentity('dwpose').changelog, 'dwpose-generator');
for(const service of ['wan22-animate2','wan22-i2v','wan21-t2v','wan21-i2v','minimax-h3-i2v','minimax-h3-ref2va','minimax-h3-image'])
  assert.equal(generatorPageIdentity(service).changelog,`${service}-generator`);
assert.deepEqual(Object.keys(generatorPages).sort(),['dwpose','kimodo','minimax-h3-i2v','minimax-h3-image','minimax-h3-ref2va','wan21-i2v','wan21-t2v','wan22-animate2','wan22-i2v','wan22-vace'].sort());
for(const value of ['__proto__','toString','missing','']) assert.throws(()=>generatorPageIdentity(value));
