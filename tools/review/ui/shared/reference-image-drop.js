// Gradio가 이미지 교체 중 await 후에도 파일을 읽도록 drop 시점에 보존한다.
// 업로드·검증·change 처리는 Gradio에 맡기고 별도 업로드를 실행하지 않는다.
if (!document.referenceImageDropCaptureInstalled) {
    document.addEventListener('drop', function preserveReferenceDropFiles(currentDropEvent) {
        const currentDropTarget = currentDropEvent.target;
        if (!(currentDropTarget instanceof Element) ||
            !currentDropTarget.closest('.reference-upload-card')) return;
        const currentDropTransfer = currentDropEvent.dataTransfer;
        if (!currentDropTransfer || currentDropTransfer.files.length === 0) return;
        // OS 드롭의 DataTransfer는 이벤트 종료 후 파일 접근이 보호된다.
        // 합성 저장소는 그 수명에 묶이지 않으며 같은 File 객체를 유지한다.
        const retainedDropTransfer = new DataTransfer();
        for (const currentDropFile of Array.from(currentDropTransfer.files)) {
            retainedDropTransfer.items.add(currentDropFile);
        }
        Object.defineProperty(currentDropEvent, 'dataTransfer', {value: retainedDropTransfer});
    }, {capture: true});
    document.referenceImageDropCaptureInstalled = true;
}
