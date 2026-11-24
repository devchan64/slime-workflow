import test from 'node:test';
import assert from 'node:assert/strict';
import {validBillboardCatalogPage,billboardCategoryLabel} from '../../gui/billboardCatalogPage.mjs';

test('빌보드 페이지의 표시 내용과 페이지 경계를 확인한다',()=>{
  const request={offset:0,limit:10};
  const asset={id:'tree',name:'나무',category:'vegetation',modeling:{purpose:'배경'},maps:[{map:'field',source_path:'field.yaml',occurrences:1}]};
  const page={offset:0,limit:10,total:1,next_offset:null,items:[asset]};
  assert.equal(validBillboardCatalogPage(page,request),true);
  for(const invalid of [
    {...page,next_offset:10}, {...page,total:2}, {...page,offset:10},
    {...page,items:[{...asset,modeling:{purpose:{}}}]},
    {...page,items:[{...asset,maps:[{map:'field',source_path:'field.yaml',occurrences:{}}]}]},
    {...page,total:2,items:[asset,asset]},
  ])assert.equal(validBillboardCatalogPage(invalid,request),false);
  assert.equal(validBillboardCatalogPage({offset:10,limit:10,total:1,next_offset:null,items:[]},{offset:10,limit:10}),true);
});

test('알 수 없는 분류와 객체 기본 속성을 안전하게 표시한다',()=>{
  const categories={vegetation:'식생'};
  assert.equal(billboardCategoryLabel(categories,'vegetation'),'식생');
  assert.equal(billboardCategoryLabel(categories,'__proto__'),'분류 확인 불가');
});
