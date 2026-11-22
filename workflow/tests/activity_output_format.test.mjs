import test from "node:test";
import assert from "node:assert/strict";
import {formatActivityOutput} from "../../gui/formatActivityOutput.mjs";

test("formats JSON while retaining numeric tokens and escaped strings",()=>{
  const raw='{"big":9007199254740993123456789,"fraction":1.234567890123456789,"text":"quote \\\" {,} \\\\ slash","nested":[null,true,{},[]]}';
  const formatted=formatActivityOutput(raw);
  assert.match(formatted,/9007199254740993123456789/);
  assert.match(formatted,/1\.234567890123456789/);
  assert.deepEqual(JSON.parse(formatted),JSON.parse(raw));
  assert.notEqual(formatted,raw);
});

test("leaves non-JSON and incomplete output unformatted",()=>{
  assert.equal(formatActivityOutput('{"partial":'),"");
  assert.equal(formatActivityOutput('plain text'),"");
  assert.equal(formatActivityOutput('42'),"");
});

test("keeps unusually large or deeply nested output in its original form",()=>{
  assert.equal(formatActivityOutput('['.repeat(101)+'0'+']'.repeat(101)),"");
  assert.equal(formatActivityOutput(JSON.stringify({text:'a'.repeat(100000)})),"");
});
