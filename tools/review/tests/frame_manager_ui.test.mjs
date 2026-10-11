import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {test} from 'node:test';

const currentTemplateSource=readFileSync(new URL('../ui/asset_review/frame-manager.html',import.meta.url),'utf8');
const currentPageRecords=[{id:'walk-review'},{id:'walk-anchors'},{id:'standing-anchors'},{id:'map-review-iseulon'},{id:'animation-1'}];
function evaluateManagerRedirect(currentSourceHref,currentHistoryState=null){
 const currentElementRecords={'#managementLink':{},'#navigationStatus':{}};
 let currentRedirectTarget=null;
 const currentExecutionContext=vm.createContext({URL,decodeURIComponent,location:{href:currentSourceHref,replace:currentTargetHref=>{currentRedirectTarget=currentTargetHref;}},history:{state:currentHistoryState},document:{querySelector:currentSelectorText=>currentElementRecords[currentSelectorText]}});
 vm.runInContext(currentTemplateSource.split('<script>')[1].split('</script>')[0].replace('__MANAGER_PAGES__',JSON.stringify(currentPageRecords)),currentExecutionContext);
 return {target:currentRedirectTarget,message:currentElementRecords['#navigationStatus'].textContent,link:currentElementRecords['#managementLink'].href};
}
test('이전 해시 주소와 저장 검색·분류를 같은 서버의 공용 메뉴로 연결한다',()=>{
 const currentResult=evaluateManagerRedirect('http://localhost:8770/preview.html#walk-anchors',{pageIdentifier:'walk-anchors',searchQueryText:'걷기 앵커',selectedCategoryName:'animation'});
 const currentTargetUrl=new URL(currentResult.target);
 assert.equal(currentTargetUrl.origin,'http://localhost:8770');assert.equal(currentTargetUrl.pathname,'/management/');
 assert.equal(currentTargetUrl.searchParams.get('tool'),'walk-anchors');assert.equal(currentTargetUrl.searchParams.get('search'),'걷기 앵커');assert.equal(currentTargetUrl.searchParams.get('category'),'animation');assert.equal(currentTargetUrl.hash,'');assert.equal(currentResult.link,currentResult.target);
});
test('명시적 쿼리가 이전 상태보다 우선하며 동작·전장·언어를 유지한다',()=>{
 const currentTargetUrl=new URL(evaluateManagerRedirect('http://localhost:8770/preview.html?tool=standing-anchors&search=idle&action=walk&field=all&locale=en#walk-anchors',{pageIdentifier:'standing-anchors',searchQueryText:'old'}).target);
 assert.equal(currentTargetUrl.searchParams.get('tool'),'standing-anchors');assert.equal(currentTargetUrl.searchParams.get('search'),'idle');assert.equal(currentTargetUrl.searchParams.get('action'),'walk');assert.equal(currentTargetUrl.searchParams.get('field'),'all');assert.equal(currentTargetUrl.searchParams.get('locale'),'en');
 assert.equal(new URL(evaluateManagerRedirect('http://localhost/preview.html#map-reviewdetails').target).searchParams.get('tool'),'map-review');
 assert.equal(new URL(evaluateManagerRedirect('http://localhost/preview.html#animation-3').target).searchParams.get('tool'),'animation-3');
});
test('미등록 대상·깨진 해시·파일 직접 실행은 자동 이동하지 않는다',()=>{
 for(const currentSourceHref of ['http://localhost/preview.html#missing','http://localhost/preview.html#%ZZ','file:///tmp/preview.html']){
  const currentResult=evaluateManagerRedirect(currentSourceHref);assert.equal(currentResult.target,null);assert.ok(currentResult.message);
 }
 assert.equal(evaluateManagerRedirect('http://localhost/preview.html').target,'http://localhost/management/');
});
test('호환 문서는 자식 문서를 만들거나 실행 코드를 재구성하지 않는다',()=>{
 assert.doesNotMatch(currentTemplateSource,/<iframe|createElement\(['"]iframe|contentDocument|contentWindow|srcdoc/);
});
