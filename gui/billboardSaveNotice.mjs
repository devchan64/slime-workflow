export function billboardSaveNotice(record,id) {
  const ledger=record?.ledger_status_at_save==='pending' ? ' · 저장 당시 원장 반영 대기' : '';
  return `공용 속성 저장 완료 · 접수 ${id}${ledger}`;
}
