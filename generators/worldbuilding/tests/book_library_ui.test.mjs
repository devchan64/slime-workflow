import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const currentElementLookup = new Map();
function createTestElement(currentTagName='div') {
    return {tagName:currentTagName,value:'',textContent:'',hidden:false,disabled:false,children:[],attributes:{},append(...currentChildEntries){this.children.push(...currentChildEntries);},replaceChildren(...currentChildEntries){this.children=[...currentChildEntries];},setAttribute(currentAttributeName,currentAttributeValue){this.attributes[currentAttributeName]=currentAttributeValue;}};
}
const currentDocumentAdapter = {createElement:createTestElement,querySelector(currentSelectorText){if(!currentElementLookup.has(currentSelectorText))currentElementLookup.set(currentSelectorText,createTestElement());return currentElementLookup.get(currentSelectorText);},querySelectorAll(){return [...currentElementLookup.values()];}};
const currentSentRequests = [];
const currentTaskIdentifier = '20260923-234000-12345678';
const currentStageEntries = ['문서 요약','목차 구성','원문 순서 재구성','문서 정리·검수'].map((currentStageLabel,currentStageIndex)=>({stage_number:currentStageIndex+1,stage_label:currentStageLabel,current_stage_name:currentStageIndex===0?'completed':currentStageIndex===1?'failed':'skipped',run_directory:'/private/jobs/'+currentTaskIdentifier+'/stages/'+currentStageIndex,artifacts:[{relative_path:'stages/'+currentStageIndex+'/execution.log'}]}));
let currentActiveTasks = [];
const currentFetchAdapter = async (currentRequestUrl,currentRequestOptions) => {
    const currentRequestValues = currentRequestOptions?.body ? JSON.parse(currentRequestOptions.body) : null;
    currentSentRequests.push({url:currentRequestUrl,body:currentRequestValues});
    let currentResponseValues;
    if(currentRequestUrl.endsWith('/state')) currentResponseValues={management_csrf_token:'test-token',runtime_prepared_flag:true};
    else if(currentRequestUrl.endsWith('/books')) currentResponseValues={collection_entries:[{collection_id:'world',book_title_text:'세계관',source_directory_paths:['world']},{collection_id:'system-design',book_title_text:'시스템 설계',source_directory_paths:['gameplay']}],source_directory_paths:['world','gameplay'],book_entries:[],reorganization_entries:[]};
    else if(currentRequestUrl.includes('/book-jobs?')) currentResponseValues={job_entries:[{workflow_task_id:currentTaskIdentifier,book_edit_stage_name:'all-stages',current_stage_name:'failed',stage_entries:currentStageEntries,run_directory:'/private/jobs/'+currentTaskIdentifier}],active_task_identifiers:currentActiveTasks,total_count:1,page_size:20};
    else if(currentRequestUrl.endsWith('/book-ai')) {currentActiveTasks=[currentTaskIdentifier];currentResponseValues={workflow_task_id:currentTaskIdentifier};}
    else if(currentRequestUrl.endsWith('/book-job-detail')) currentResponseValues={collection_id:'world',workflow_task_id:currentTaskIdentifier,current_stage_name:'failed',stage_entries:currentStageEntries,run_directory:'/private/jobs/'+currentTaskIdentifier,artifacts:[{relative_path:'execution.log',byte_count:10}]};
    else if(currentRequestUrl.endsWith('/book-job-record')) currentResponseValues={absolute_path:'/private/jobs/'+currentTaskIdentifier+'/'+currentRequestValues.relative_path,content_text:'<script>실패 원인</script>',read_url:'/record',truncated_flag:false};
    else throw new Error('예상하지 못한 API: '+currentRequestUrl);
    return {ok:true,json:async()=>currentResponseValues};
};
const currentTestContext=vm.createContext({document:currentDocumentAdapter,fetch:currentFetchAdapter,setInterval(){},console,encodeURIComponent});
const currentHtmlSource=readFileSync(new URL('../book-library.html',import.meta.url),'utf8');
vm.runInContext(currentHtmlSource.split('<script>')[1].split('</script>')[0],currentTestContext);
vm.runInContext(readFileSync(new URL('../book-library-jobs.js',import.meta.url),'utf8'),currentTestContext);
await new Promise(currentResolveTask=>setImmediate(currentResolveTask));
assert.equal(currentElementLookup.get('#automateBook').disabled,false);
currentDocumentAdapter.querySelector('#bookEditInstruction').value='내용을 보존하며 네 단계를 실행한다.';
await currentElementLookup.get('#automateBook').onclick();
assert.equal(currentSentRequests.filter(currentRequestEntry=>currentRequestEntry.url.endsWith('/book-ai')).length,1);
assert.equal(currentSentRequests.find(currentRequestEntry=>currentRequestEntry.url.endsWith('/book-ai')).body.book_edit_stage_name,'all-stages');
assert.equal(currentElementLookup.get('#automateBook').disabled,true);
assert.equal(currentElementLookup.get('#jobDetailPanel').hidden,false);
assert.equal(currentElementLookup.get('#jobStageList').children.length,4);
assert.match(currentElementLookup.get('#jobStageList').children[2].children[0].textContent,/실행 안 함/);
await vm.runInContext(`showAutomationRecord('${currentTaskIdentifier}','stages/1/execution.log')`,currentTestContext);
assert.equal(currentElementLookup.get('#recordContentText').textContent,'<script>실패 원인</script>');
assert.match(currentElementLookup.get('#recordPathText').textContent,/stages\/1\/execution.log/);
assert.equal(currentElementLookup.get('#recordViewerPanel').hidden,false);
assert.equal(currentElementLookup.get('#historyPreviousPage').disabled,true);
assert.equal(currentElementLookup.get('#historyNextPage').disabled,true);
console.log('도서 UI: 전체 실행 요청·중복 방지·실패 단계·기록 경로·안전한 본문 표시 통과');
