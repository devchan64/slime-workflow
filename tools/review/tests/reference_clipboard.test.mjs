import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {test} from 'node:test';
const clipboardSourceCode = readFileSync(new URL('../ui/shared/reference-clipboard.js',import.meta.url),'utf8');
function createClipboardHarness(clipboardReadCallback) {
    const registeredClickHandlers = {};
    const clipboardStatusElement = {textContent:''};
    const referenceUploadInput = {dispatchEvent(event){this.lastEvent=event;},click(){this.clicked=true;}};
    const clipboardTestContext = {
        element:{closest(){return {querySelector(){return referenceUploadInput;}};},querySelector(selector){return selector==='[role="status"]'?clipboardStatusElement:{addEventListener(event,callback){registeredClickHandlers[selector]=callback;}};}},
        navigator:{clipboard:{read:clipboardReadCallback}},
        DataTransfer:class {constructor(){this.files=[];this.items={add:file=>this.files.push(file)};}},
        File:class {constructor(parts,name,options){this.name=name;this.type=options.type;}},Event:class {constructor(type){this.type=type;}}
    };
    vm.runInNewContext(clipboardSourceCode,clipboardTestContext);
    return {registeredClickHandlers,clipboardStatusElement,referenceUploadInput};
}
test('한 번 클릭하면 선택한 카드 업로드 입력에 이미지를 전달한다',async()=>{
    const currentTestHarness=createClipboardHarness(async()=>[{types:['image/png'],getType:async()=>({type:'image/png'})}]);
    await currentTestHarness.registeredClickHandlers['[data-reference-action="clipboard"]']();
    assert.equal(currentTestHarness.referenceUploadInput.files[0].name,'clipboard.png');
    assert.equal(currentTestHarness.referenceUploadInput.lastEvent.type,'change');
});
test('이미지가 없거나 권한이 거부되면 안내한다',async()=>{
    for(const clipboardReadCallback of [async()=>[],async()=>{throw Object.assign(new Error(),{name:'NotAllowedError'});}]){
        const currentTestHarness=createClipboardHarness(clipboardReadCallback);
        await currentTestHarness.registeredClickHandlers['[data-reference-action="clipboard"]']();
        assert.match(currentTestHarness.clipboardStatusElement.textContent,/이미지가 없습니다|권한이 거부/);
        assert.equal(currentTestHarness.referenceUploadInput.lastEvent,undefined);
    }
});
test('파일 불러오기는 같은 카드의 파일 선택창을 연다',()=>{
    const currentTestHarness=createClipboardHarness(async()=>[]);
    currentTestHarness.registeredClickHandlers['[data-reference-action="upload"]']();
    assert.equal(currentTestHarness.referenceUploadInput.clicked,true);
});
