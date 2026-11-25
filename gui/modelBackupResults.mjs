export function validBackupModels(value) {
  if(!value || typeof value!=='object' || !Array.isArray(value.models) || (value.backup_error!=null && typeof value.backup_error!=='string'))return false;
  const names=new Set();
  return value.models.every(model=>{
    if(!model || typeof model!=='object' || Array.isArray(model) || typeof model.name!=='string' || !model.name.trim() || names.has(model.name) ||
      (model.relative_path!=null && typeof model.relative_path!=='string') || !['local_present','backup_present','snapshot_present'].every(key=>model[key]==null || typeof model[key]==='boolean'))return false;
    names.add(model.name);return true;
  });
}

export function backupActionReasons({busy,modelsLoading,modelsError,backupError,selected,localMissing,target,pendingRequest}) {
  const base=busy ? '현재 요청이 끝날 때까지 기다리세요.' : modelsLoading ? '모델 목록을 불러오는 중입니다.' : modelsError ? '모델 목록을 다시 불러오세요.' : !selected ? '모델 디렉터리를 선택하세요.' : '';
  return {
    compare:base || (backupError ? '백업 연결을 확인하고 목록을 다시 불러오세요.' : localMissing ? '로컬 모델이 없어 백업과 비교할 수 없습니다.' : target==='snapshot_manifest' ? '자체 무결성은 크기·시간 비교를 지원하지 않습니다.' : ''),
    metadata:base,
    verify:base || (backupError ? '백업 연결을 확인하고 목록을 다시 불러오세요.' : localMissing && target!=='snapshot_manifest' ? '로컬 모델이 없어 이 대상을 검증할 수 없습니다.' : pendingRequest ? '이전 요청의 접수 결과를 먼저 확인하세요.' : ''),
    sync:base || (backupError ? '백업 연결을 확인하고 목록을 다시 불러오세요.' : localMissing ? '로컬 모델이 없어 새 백업을 만들 수 없습니다.' : pendingRequest ? '이전 요청의 접수 결과를 먼저 확인하세요.' : ''),
  };
}

export function validBackupMetadata(value,model) {
  const strings=(item,keys)=>item && typeof item==='object' && !Array.isArray(item) && keys.every(key=>item[key]==null || typeof item[key]==='string');
  return Boolean(strings(value,['model','origin','snapshot_id','manifest_state']) && value.model===model && Array.isArray(value.services) && value.services.every(service=>typeof service==='string') &&
    Array.isArray(value.declared_sources) && value.declared_sources.every(item=>strings(item,['repository','revision'])) &&
    Array.isArray(value.declared_files) && value.declared_files.every(item=>strings(item,['path','sha256'])));
}

export function validBackupComparison(value,model,target) {
  return Boolean(value && typeof value==='object' && !Array.isArray(value) && value.model===model && value.target===target &&
    typeof value.complete==='boolean' && ['sha256','size_and_mtime'].includes(value.comparison_basis) && Array.isArray(value.files) &&
    value.files.every(file=>file && typeof file==='object' && !Array.isArray(file) && typeof file.path==='string' && typeof file.status==='string') &&
    ['source_errors','backup_errors'].every(key=>value[key]==null || (Array.isArray(value[key]) && value[key].every(item=>item && typeof item==='object' && typeof item.path==='string' && typeof item.reason==='string'))));
}

export function validBackupJob(value,jobId) {
  if (!value || typeof value!=='object' || Array.isArray(value) || value.job_id!==jobId || typeof value.status!=='string') return false;
  if (!['model','operation','started_at','finished_at','error'].every(key=>value[key]==null || typeof value[key]==='string')) return false;
  const result=value.result;
  if (result==null) return true;
  if (typeof result!=='object' || Array.isArray(result)) return false;
  return result.files==null || (typeof value.model==='string' && typeof value.target==='string' && validBackupComparison(result,value.model,value.target));
}

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
  if (!result || result.comparison_basis !== 'sha256' || typeof result.complete !== 'boolean' || !Array.isArray(result.files) || result.files.some(file=>!file || typeof file!=='object' || Array.isArray(file) || typeof file.status!=='string')) return null;
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
