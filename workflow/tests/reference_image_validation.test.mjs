import {test} from 'node:test';
import assert from 'node:assert/strict';
import {referenceImageError,clipboardImageName} from '../../gui/referenceImageValidation.mjs';
test('참조 입력은 슬롯의 형식과 파일 크기를 확인한다',()=>{
  assert.equal(referenceImageError({type:'image/png',size:3000000},'image/png',3000000),'');
  assert.match(referenceImageError({type:'image/png',size:3000001},'image/png',3000000),/3MB/);
  assert.match(referenceImageError({type:'image/jpeg',size:10},'image/png',3000000),/PNG/);
  assert.equal(referenceImageError({type:'image/jpeg',size:10},'image/*',null),'');
  assert.match(referenceImageError({type:'text/plain',size:10},'image/*',null),/이미지/);
});
test('클립보드 파일명은 이미지 종류에 맞는다',()=>{
  assert.equal(clipboardImageName('image/png'),'clipboard.png');
  assert.equal(clipboardImageName('image/jpeg'),'clipboard.jpg');
  assert.equal(clipboardImageName('image/webp'),'clipboard.webp');
  assert.equal(clipboardImageName('image/unknown'),'clipboard.img');
});
