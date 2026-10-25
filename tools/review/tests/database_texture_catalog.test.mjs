import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('DB 신규 빌보드는 정적 카탈로그 없이 선택 리소스가 된다',()=>{
 const currentSourceText=readFileSync(new URL('../ui/map/block-map-review.js',import.meta.url),'utf8');
 const currentLoopSource=currentSourceText.slice(currentSourceText.indexOf('for(const currentResourceKey of currentResourceKeys){'),currentSourceText.indexOf('const loadedTextureImages='));
 const currentDatabaseImage={url:'/management/map-assets/database-images/abc',sha256:'abc',width:128,height:96,assetType:'props'};
 const currentContextValues={currentResourceKeys:['new-cart'],currentMapRecord:{imageManifest:{'new-cart':currentDatabaseImage}},currentTextureRecords:{},currentSelectedTextureRecords:{},currentSelectedGameKeys:{}};
 vm.runInNewContext(currentLoopSource,currentContextValues);
 assert.equal(currentContextValues.currentSelectedTextureRecords['new-cart'].billboard_category,'props');
 assert.equal(currentContextValues.currentSelectedTextureRecords['new-cart'].path,currentDatabaseImage.url);
 assert.equal(currentContextValues.currentSelectedGameKeys['new-cart'],'new-cart');
 currentDatabaseImage.assetType='invalid';
 assert.throws(()=>vm.runInNewContext(currentLoopSource,currentContextValues),/분류 오류/);
});
