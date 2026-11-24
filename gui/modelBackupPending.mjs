export function readPendingBackupRequest(storage) {
  try {
    const request = JSON.parse(storage.getItem('model-backup-pending') || 'null');
    if (!request || !['backup-sync', 'backup-verify'].includes(request.command)) return null;
    const payload = request.payload;
    if (!payload || typeof payload.model !== 'string' || !payload.model ||
        !/^[0-9a-f]{32}$/.test(payload.request_id)) return null;
    const allowed = request.command === 'backup-sync' ? ['model', 'request_id'] : ['model', 'request_id', 'target'];
    if (Object.keys(payload).some(key => !allowed.includes(key))) return null;
    if (request.command === 'backup-verify' && !['canonical', 'latest_snapshot', 'snapshot_manifest'].includes(payload.target)) return null;
    return request;
  } catch {
    return null;
  }
}

export function validateBackupReceipt(request, receipt) {
  const expectedOperation = request.command === 'backup-sync' ? 'sync' : 'verify';
  if (!receipt || receipt.job_id !== request.payload.request_id || receipt.model !== request.payload.model ||
      receipt.operation !== expectedOperation || !['running', 'completed', 'failed', 'interrupted', 'unknown'].includes(receipt.status)) {
    throw new Error('접수 응답이 요청과 일치하지 않습니다. 이력에서 작업을 확인하세요.');
  }
  if (receipt.target !== undefined && receipt.target !== (request.payload.target || 'canonical')) {
    throw new Error('접수 응답의 검증 대상이 요청과 일치하지 않습니다. 이력에서 작업을 확인하세요.');
  }
  return receipt;
}
