// 공용 참조 카드 안에서 Gradio 업로드 입력으로 전달한다.
const referenceCardElement = element.closest('.reference-upload-slot');
const clipboardActionButton = element.querySelector('[data-reference-action="clipboard"]');
const clipboardStatusElement = element.querySelector('[role="status"]');
element.querySelector('[data-reference-action="upload"]').addEventListener('click', () => {
    const referenceUploadInput = referenceCardElement.querySelector('input[type="file"]');
    if (referenceUploadInput) referenceUploadInput.click();
    else clipboardStatusElement.textContent = '현재 이미지를 지운 뒤 새 파일을 불러오세요.';
});
clipboardActionButton.addEventListener('click', async () => {
    clipboardStatusElement.textContent = '';
    try {
        if (!navigator.clipboard?.read) throw new Error('이 브라우저는 이미지 클립보드 읽기를 지원하지 않습니다. 파일 업로드를 사용하세요.');
        const clipboardItemRecords = await navigator.clipboard.read();
        let selectedImageBlob = null;
        for (const clipboardItemRecord of clipboardItemRecords) {
            const clipboardImageType = clipboardItemRecord.types.find(type => type.startsWith('image/'));
            if (clipboardImageType) {
                selectedImageBlob = await clipboardItemRecord.getType(clipboardImageType);
                break;
            }
        }
        if (!selectedImageBlob) throw new Error('클립보드에 이미지가 없습니다. 이미지를 복사한 뒤 다시 누르세요.');
        const referenceUploadInput = referenceCardElement.querySelector('input[type="file"]');
        if (!referenceUploadInput) throw new Error('현재 이미지를 지운 뒤 다시 붙여넣으세요.');
        const clipboardFileTransfer = new DataTransfer();
        clipboardFileTransfer.items.add(new File([selectedImageBlob], 'clipboard.' + selectedImageBlob.type.split('/')[1], {type: selectedImageBlob.type}));
        referenceUploadInput.files = clipboardFileTransfer.files;
        referenceUploadInput.dispatchEvent(new Event('change', {bubbles: true}));
        clipboardStatusElement.textContent = '이미지를 전달했습니다. 미리보기를 확인하세요.';
    } catch (clipboardReadError) {
        clipboardStatusElement.textContent = clipboardReadError.name === 'NotAllowedError'
            ? '클립보드 읽기 권한이 거부되었습니다. 브라우저 권한을 허용하거나 파일 업로드를 사용하세요.'
            : clipboardReadError.message;
    }
});
