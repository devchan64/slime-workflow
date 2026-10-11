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

// 실제 브라우저 화면 높이를 기준으로 참조를 확인한다.
if (!document.referencePreviewCaptureInstalled) {
    const referencePreviewViewportRatio = 0.8;
    document.addEventListener('click', function openReferenceImagePreview(currentClickEvent) {
        if (!(currentClickEvent.target instanceof Element)) return;
        const selectedPreviewButton = currentClickEvent.target.closest('button');
        if (!selectedPreviewButton?.closest('.reference-upload-card') ||
            !['Fullscreen', '전체 화면'].includes(selectedPreviewButton.getAttribute('aria-label') || selectedPreviewButton.getAttribute('title'))) return;
        const selectedReferenceImage = selectedPreviewButton.closest('.reference-upload-card').querySelector('img');
        if (!selectedReferenceImage?.src) return;
        currentClickEvent.preventDefault();
        currentClickEvent.stopImmediatePropagation();
        const previewOwnerDocument = window.top.document;
        const referencePreviewDialog = previewOwnerDocument.createElement('dialog');
        referencePreviewDialog.setAttribute('aria-label', '참조 이미지 미리보기');
        const referencePreviewImage = previewOwnerDocument.createElement('img');
        referencePreviewImage.src = selectedReferenceImage.src;
        referencePreviewImage.alt = selectedReferenceImage.alt || '참조 이미지';
        const closePreviewButton = previewOwnerDocument.createElement('button');
        closePreviewButton.textContent = '닫기';
        closePreviewButton.addEventListener('click', () => referencePreviewDialog.close());
        const resizeReferencePreview = () => {
            referencePreviewImage.style.maxWidth = `${window.top.innerWidth * referencePreviewViewportRatio}px`;
            referencePreviewImage.style.maxHeight = `${window.top.innerHeight * referencePreviewViewportRatio}px`;
            referencePreviewImage.style.display = 'block';
            referencePreviewImage.style.objectFit = 'contain';
        };
        resizeReferencePreview();
        window.top.addEventListener('resize', resizeReferencePreview);
        referencePreviewDialog.addEventListener('close', () => {
            window.top.removeEventListener('resize', resizeReferencePreview);
            referencePreviewDialog.remove();
            selectedPreviewButton.focus();
        }, {once: true});
        referencePreviewDialog.append(referencePreviewImage, closePreviewButton);
        previewOwnerDocument.body.append(referencePreviewDialog);
        referencePreviewDialog.showModal();
        closePreviewButton.focus();
    }, {capture: true});
    document.referencePreviewCaptureInstalled = true;
}
