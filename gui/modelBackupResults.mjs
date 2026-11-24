export function modelBackupPage(files, filter, page, pageSize = 100) {
  const counts = Object.create(null);
  for (const file of files) counts[file.status] = (counts[file.status] || 0) + 1;
  const filtered = files.filter(file => filter === 'all' || file.status === filter);
  const lastPage = Math.max(0, Math.ceil(filtered.length / pageSize) - 1);
  const currentPage = Math.min(Math.max(0, page), lastPage);
  return {counts, total: filtered.length, page: currentPage,
          files: filtered.slice(currentPage * pageSize, (currentPage + 1) * pageSize)};
}

export function verificationSummary(result) {
  if (!result || result.comparison_basis !== 'sha256' || !Array.isArray(result.files)) return null;
  if (!result.complete) return '일부 경로를 확인하지 못해 전체 일치를 판단할 수 없습니다.';
  if (!result.files.length) return '검증할 파일이 없어 전체 일치를 판단할 수 없습니다.';
  if (result.files.every(file => file.status === 'verified')) return '조회한 모든 파일의 SHA-256이 일치합니다.';
  return '일치하지 않거나 확인할 수 없는 파일이 있습니다. 아래 전체 결과를 확인하세요.';
}

export function backupTargetLabel(target) {
  return ({canonical: '기존 공유 디렉터리와 비교', latest_snapshot: '최근 스냅샷과 비교',
    snapshot_manifest: '스냅샷 자체 무결성', legacy: '이관 전 공유 디렉터리와 비교'}[target] || '대상 확인 불가');
}

export function backupDirectories(files, directory = '') {
  const prefix = directory ? `${directory}/` : '';
  const children = new Map();
  for (const file of files) {
    if (!file.path.startsWith(prefix)) continue;
    const rest = file.path.slice(prefix.length);
    const slash = rest.indexOf('/');
    if (slash < 0) continue;
    const name = rest.slice(0, slash);
    if (!name) continue;
    const item = children.get(name) || {name, path: prefix + name, count: 0, statuses: Object.create(null)};
    item.count++;
    item.statuses[file.status] = (item.statuses[file.status] || 0) + 1;
    children.set(name, item);
  }
  return [...children.values()].sort((a, b) => a.name.localeCompare(b.name));
}
