import assert from 'node:assert/strict';
import {generatorPageIdentity, generatorPages} from '../../gui/generatorPageRegistry.mjs';
assert.equal(generatorPageIdentity('kimodo').changelog, 'kimodo-generator');
assert.equal(generatorPageIdentity('wan22-vace').changelog, 'wan22-vace-generator');
assert.equal(generatorPageIdentity('dwpose').changelog, 'dwpose-generator');
assert.equal(Object.keys(generatorPages).length,3);
for(const value of ['__proto__','toString','missing','']) assert.throws(()=>generatorPageIdentity(value));
