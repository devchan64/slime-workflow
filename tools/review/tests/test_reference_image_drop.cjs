const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {test} = require('node:test');
const currentScriptSource = fs.readFileSync('tools/review/ui/shared/reference-image-drop.js', 'utf8');

function createDropTestContext() {
    const registeredDropHandlers = [];
    class ReferenceDropTarget {
        constructor(currentReferenceMatch) { this.currentReferenceMatch = currentReferenceMatch; }
        closest() { return this.currentReferenceMatch; }
    }
    class RetainedDropTransfer {
        constructor() {
            this.files = [];
            this.items = {add: currentDropFile => this.files.push(currentDropFile)};
        }
    }
    const currentBrowserContext = vm.createContext({
        document: {addEventListener: (...currentListenerArguments) => registeredDropHandlers.push(currentListenerArguments)},
        Element: ReferenceDropTarget, DataTransfer: RetainedDropTransfer,
    });
    vm.runInContext(currentScriptSource, currentBrowserContext);
    return {registeredDropHandlers, currentBrowserContext, ReferenceDropTarget};
}

test('기존 이미지 교체: 이벤트 종료와 비동기 갱신 후에도 첫 드롭 파일 유지', async () => {
    const {registeredDropHandlers, ReferenceDropTarget} = createDropTestContext();
    const uploadedReferenceFile = {name: 'replacement.png'};
    const originalDropTransfer = {files: [uploadedReferenceFile]};
    const currentDropEvent = {target: new ReferenceDropTarget(true), dataTransfer: originalDropTransfer};
    registeredDropHandlers[0][1](currentDropEvent);
    originalDropTransfer.files = []; // 네이티브 drop 종료 후 보호 모드
    await Promise.resolve(); // Gradio 기존 이미지 초기화와 화면 갱신
    assert.equal(currentDropEvent.dataTransfer.files.length, 1);
    assert.equal(currentDropEvent.dataTransfer.files[0], uploadedReferenceFile);
    assert.equal(registeredDropHandlers[0][2].capture, true);
});

test('빈 슬롯·반복 교체마다 새 파일만 전달', () => {
    const {registeredDropHandlers, ReferenceDropTarget} = createDropTestContext();
    for (const currentFileName of ['first.png', 'second.png', 'second.png']) {
        const currentDropFile = {name: currentFileName};
        const currentDropEvent = {target: new ReferenceDropTarget(true), dataTransfer: {files: [currentDropFile]}};
        registeredDropHandlers[0][1](currentDropEvent);
        assert.equal(currentDropEvent.dataTransfer.files.length, 1);
        assert.equal(currentDropEvent.dataTransfer.files[0], currentDropFile);
    }
});

test('다른 입력·빈 드롭은 변경하지 않고 재마운트 시 중복 설치하지 않음', () => {
    const {registeredDropHandlers, currentBrowserContext, ReferenceDropTarget} = createDropTestContext();
    for (const currentReferenceMatch of [false, true]) {
        const originalDropTransfer = {files: currentReferenceMatch ? [] : [{name: 'outside.png'}]};
        const currentDropEvent = {target: new ReferenceDropTarget(currentReferenceMatch), dataTransfer: originalDropTransfer};
        registeredDropHandlers[0][1](currentDropEvent);
        assert.equal(currentDropEvent.dataTransfer, originalDropTransfer);
    }
    vm.runInContext(currentScriptSource, currentBrowserContext);
    assert.equal(registeredDropHandlers.length, 1);
});
