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
