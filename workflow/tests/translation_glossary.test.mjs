import test from 'node:test';
import assert from 'node:assert/strict';
import {parseTranslationGlossary} from '../../gui/translationGlossary.mjs';
test('glossary accepts unambiguous pairs and rejects malformed or duplicate sources',()=>{
 assert.deepEqual(parseTranslationGlossary(' 이슬온 => Iseulon\n\n나무 => tree '),[{source:'이슬온',target:'Iseulon'},{source:'나무',target:'tree'}]);
 for(const input of ['형식 오류','나무 =>','=> tree','a => b => c','a => b\na => c','a'.repeat(101)+' => b',Array.from({length:51},(_,i)=>`${i} => b`).join('\n')])assert.throws(()=>parseTranslationGlossary(input));
});
