async (identifier) => {
 if (!identifier || document.querySelector('[data-history-delete-dialog]')) return [identifier, false];
 const accepted = await new Promise(resolve => {
  const dialog = document.createElement('dialog');
  dialog.dataset.historyDeleteDialog = 'true';
  dialog.setAttribute('aria-label', '선택 이력 삭제 확인');
  dialog.style.cssText = 'max-width:480px;width:calc(100% - 32px);padding:20px;border:1px solid var(--border-subtle,#52647c);border-radius:10px;background:var(--surface-panel,#192230);color:var(--text-primary,#edf3fc)';
  const title = document.createElement('h3');
  title.textContent = '선택한 생성 이력을 삭제할까요?';
  const job = document.createElement('p');
  job.textContent = 'ID: ' + identifier;
  job.style.overflowWrap = 'anywhere';
  const note = document.createElement('p');
  note.textContent = '현재 생성기의 정리 정책: ' + __DELETION_SCOPE_TEXT__ + ' 개별 삭제는 위 ID의 작업에만 적용됩니다.';
  const actions = document.createElement('div');
  actions.style.cssText = 'display:flex;justify-content:flex-end;gap:8px';
  const cancel = document.createElement('button');
  cancel.type = 'button'; cancel.textContent = '취소';
  const confirm = document.createElement('button');
  confirm.type = 'button'; confirm.textContent = '이력 삭제';
  const finish = value => { dialog.close(); dialog.remove(); resolve(value); };
  cancel.onclick = () => finish(false);
  confirm.onclick = () => finish(true);
  dialog.addEventListener('cancel', event => { event.preventDefault(); finish(false); });
  actions.append(cancel, confirm); dialog.append(title, job, note, actions);
  document.body.append(dialog); dialog.showModal(); cancel.focus();
 });
 return [identifier, accepted];
}
