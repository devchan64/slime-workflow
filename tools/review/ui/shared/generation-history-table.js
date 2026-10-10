watch('value', () => {
    element.querySelectorAll('input[type=radio]').forEach(currentRadioInput => {
        currentRadioInput.checked = currentRadioInput.hasAttribute('checked');
    });
});
element.addEventListener('change', currentChangeEvent => {
    const currentRadioInput = currentChangeEvent.target;
    if (currentRadioInput.matches('input[type=radio]')) {
        trigger('click', {identifier: currentRadioInput.value});
    }
});
element.addEventListener('click', async currentClickEvent => {
    const currentCopyButton = currentClickEvent.target.closest('[data-history-copy-id]');
    if (!currentCopyButton || !element.contains(currentCopyButton)) return;
    currentClickEvent.preventDefault();
    currentClickEvent.stopPropagation();
    const currentStatusElement = currentCopyButton.parentElement.querySelector('[data-history-copy-status]');
    try {
        await navigator.clipboard.writeText(currentCopyButton.dataset.historyCopyId);
        currentStatusElement.textContent = ' 복사 완료';
    } catch (currentClipboardError) {
        currentStatusElement.textContent = ' 복사 실패 · 클립보드 권한을 확인하거나 ID를 직접 선택해 복사하세요.';
    }
});
