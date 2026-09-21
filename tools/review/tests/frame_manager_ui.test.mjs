import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const sourceTemplateText=readFileSync(new URL('../frame-manager.html',import.meta.url),'utf8');
const sourcePageRecords=[
 {id:'walk-review',label:'걷기 비교',description:'2026-09-20 preview.html',category:'web-review',path:'walking/preview.html'},
 {id:'walk-anchors',label:'걷기 앵커',description:'좌표 편집',category:'web-review',path:'walking/anchors.html',anchorEditor:true},
 {id:'standing-anchors',label:'스탠딩 앵커',description:'좌표 편집',category:'web-review',path:'standing/preview.html',anchorEditor:true},
 {id:'slime',label:'슬라임 · 대기 · v1',description:'monster.slime.idle',category:'animation',path:'slime/anchors.html',anchorEditor:true}
];
const selectedElementLookup=new Map();
function createTestElement(){return {value:'',hidden:false,style:{},attributes:{},children:[],listeners:{},append(childElementRecord){this.children.push(childElementRecord);},replaceChildren(){this.children=[];},focus(){this.focused=true;},setAttribute(attributeNameValue,attributeTextValue){this.attributes[attributeNameValue]=attributeTextValue;},addEventListener(eventNameValue,eventHandlerValue){this.listeners[eventNameValue]=eventHandlerValue;}};}
const documentTestAdapter={createElement:createTestElement,querySelector(selectorTextValue){if(!selectedElementLookup.has(selectorTextValue))selectedElementLookup.set(selectorTextValue,createTestElement());return selectedElementLookup.get(selectorTextValue);}};
documentTestAdapter.querySelector('#reviewCategory').value='all';
const windowEventHandlers={};
const testLocationState={hash:''};
const testHistoryEntries=[];
let testHistoryPosition=-1;
const testHistoryAdapter={state:null,pushState(nextHistoryState,unusedTitleText,nextHashValue){testHistoryEntries.splice(testHistoryPosition+1);testHistoryEntries.push({state:nextHistoryState,hash:nextHashValue});testHistoryPosition++;this.state=nextHistoryState;testLocationState.hash=nextHashValue;},replaceState(nextHistoryState,unusedTitleText,nextHashValue){if(testHistoryPosition<0)testHistoryPosition=0;testHistoryEntries[testHistoryPosition]={state:nextHistoryState,hash:nextHashValue};this.state=nextHistoryState;testLocationState.hash=nextHashValue;},back(){if(testHistoryPosition>0){testHistoryPosition--;this.state=testHistoryEntries[testHistoryPosition].state;testLocationState.hash=testHistoryEntries[testHistoryPosition].hash;windowEventHandlers.popstate();}},forward(){if(testHistoryPosition<testHistoryEntries.length-1){testHistoryPosition++;this.state=testHistoryEntries[testHistoryPosition].state;testLocationState.hash=testHistoryEntries[testHistoryPosition].hash;windowEventHandlers.popstate();}}};
const testExecutionContext=vm.createContext({Event:class{constructor(eventNameValue){this.type=eventNameValue;}},document:documentTestAdapter,window:{addEventListener(eventNameValue,eventHandlerValue){windowEventHandlers[eventNameValue]=eventHandlerValue;}},location:testLocationState,history:testHistoryAdapter});
vm.runInContext(sourceTemplateText.split('<script>')[1].split('</script>')[0].replace('__MANAGER_PAGES__',JSON.stringify(sourcePageRecords)),testExecutionContext);
vm.runInContext(`
if(managerPaneElements.size!==1)throw new Error('선택하지 않은 페이지를 미리 로드함');
selectManagerPage('walk-anchors');
const originalAnchorPane=managerPaneElements.get('walk-anchors');
originalAnchorPane.testEditedCoordinate=123;
const originalAnchorSource=originalAnchorPane.src;
selectManagerPage('standing-anchors');
if(!originalAnchorPane.hidden)throw new Error('기존 화면 숨김 실패');
selectManagerPage('walk-anchors');
if(managerPaneElements.get('walk-anchors')!==originalAnchorPane||originalAnchorPane.src!==originalAnchorSource||originalAnchorPane.testEditedCoordinate!==123)throw new Error('메뉴 전환 중 편집 상태 소실');
if(selectManagerPage('missing')!==false)throw new Error('미지원 메뉴 허용');
if(filterManagerRecords('슬라임 대기','animation').length!==1)throw new Error('한국어 검색 실패');
if(filterManagerRecords('MONSTER.SLIME','all').length!==1)throw new Error('대소문자 ID 검색 실패');
if(filterManagerRecords('2026-09','web-review').length!==1)throw new Error('검수 날짜 검색 실패');
document.querySelector('#assetSearch').value='없는 결과';renderManagerResults();
if(document.querySelector('#assetSelection').children.length!==0||originalAnchorPane.hidden)throw new Error('빈 검색이 편집 화면에 영향을 줌');
document.querySelector('#assetSearch').value='슬라임';renderManagerResults();
if(originalAnchorPane.hidden)throw new Error('검색 도중 자동 이동');
document.querySelector('#assetSearch').onkeydown({key:'Enter',preventDefault(){}});
if(selectedPageIdentifier!=='slime')throw new Error('검색 후 Enter 선택 실패');
document.querySelector('#clearSearch').onclick();
if(filteredPageRecords.length!==4||selectedPageIdentifier!=='slime')throw new Error('검색 초기화 후 선택 소실');
`,testExecutionContext);
assert.equal(selectedElementLookup.get('#standaloneLink').href,'slime/anchors.html');
vm.runInContext(`
resetManagerFilters();selectManagerPage('walk-review');
if(!document.querySelector('#previousReview').disabled||document.querySelector('#nextReview').disabled)throw new Error('목록 경계 버튼 오류');
document.querySelector('#assetSearch').value='걷기';updateManagerFilters();
document.querySelector('#nextReview').onclick();
if(selectedPageIdentifier!=='walk-anchors'||!document.querySelector('#nextReview').disabled)throw new Error('검색 결과 내 다음 이동 실패');
history.back();
if(selectedPageIdentifier!=='walk-review'||document.querySelector('#assetSearch').value!=='걷기')throw new Error('뒤로 이동 시 검색 상태 복원 실패');
history.forward();
if(selectedPageIdentifier!=='walk-anchors'||managerPaneElements.get('walk-anchors').testEditedCoordinate!==123)throw new Error('앞으로 이동 시 편집 상태 소실');
document.querySelector('#assetSearch').value='슬라임';updateManagerFilters();
if(document.querySelector('#revealCurrentReview').hidden||!document.querySelector('#previousReview').disabled||!document.querySelector('#nextReview').disabled)throw new Error('필터 밖 현재 항목 처리 오류');
document.querySelector('#revealCurrentReview').onclick();
if(document.querySelector('#revealCurrentReview').hidden===false||selectedPageIdentifier!=='walk-anchors')throw new Error('현재 항목 찾기 실패');
document.querySelector('#toggleNavigation').onclick();
if(!document.querySelector('#managerPicker').hidden||document.querySelector('#toggleNavigation').attributes['aria-expanded']!=='false')throw new Error('탐색 영역 접기 실패');
document.querySelector('#toggleNavigation').onclick();
if(document.querySelector('#managerPicker').hidden)throw new Error('탐색 영역 펼치기 실패');
`,testExecutionContext);
vm.runInContext(`
const selectedListButton=document.querySelector('#assetSelection').children[1];
if(selectedListButton.attributes['aria-current']!=='page')throw new Error('현재 대상 강조 누락');
document.querySelector('#assetSelection').children[3].onclick();
if(selectedPageIdentifier!=='slime')throw new Error('목록 클릭 이동 실패');
`,testExecutionContext);
vm.runInContext(`
const editedPaneElement=managerPaneElements.get('slime');
const editedDocumentHandlers={};
editedPaneElement.contentDocument={body:{dataset:{coordinateDownloadPending:'false'},classList:{add(){}}},addEventListener(eventNameValue,eventHandlerValue){editedDocumentHandlers[eventNameValue]=eventHandlerValue;},dispatchEvent(currentEventRecord){this.lastEventName=currentEventRecord.type;}};
editedPaneElement.listeners.load();
if(pendingCoordinatePages.size)throw new Error('불필요한 이탈 경고');
editedPaneElement.contentDocument.body.dataset.coordinateDownloadPending='true';editedDocumentHandlers['review-coordinate-state']();
let unloadWarningRaised=false;
`,testExecutionContext);
windowEventHandlers.beforeunload({preventDefault(){vm.runInContext('unloadWarningRaised=true',testExecutionContext);}});
vm.runInContext(`
if(!unloadWarningRaised||pendingCoordinatePages.size!==1)throw new Error('이탈 경고 누락');
selectManagerPage('walk-review');
if(editedPaneElement.contentDocument.lastEventName!=='review-pane-hidden')throw new Error('숨긴 재생 일시정지 신호 누락');
editedPaneElement.contentDocument.body.dataset.coordinateDownloadPending='false';editedDocumentHandlers['review-coordinate-state']();
if(pendingCoordinatePages.size)throw new Error('다운로드 후 변경 상태 남음');
`,testExecutionContext);
console.log('검색·분류·이전/다음·브라우저 방문 기록·필터 복원·현재 위치·접기·편집 보존 통과');
