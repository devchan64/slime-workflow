import React, {useEffect, useRef, useState} from 'react';
import {managementCommand} from './managementCommand.js';
import {readPendingBackupRequest, validateBackupReceipt} from './modelBackupPending.mjs';
import {modelBackupPage} from './modelBackupResults.mjs';

const labels = {missing: '백업 누락', different: '파일 다름', matches_metadata: '크기·시간 일치', verified: 'SHA-256 일치', backup_only: '백업에만 있음', unknown: '확인 불가'};

export default function ModelBackupCompare() {
  const [models, setModels] = useState([]);
  const [selected, setSelected] = useState('');
  const [target, setTarget] = useState('canonical');
  const [comparison, setComparison] = useState(null);
  const [filter, setFilter] = useState('all');
  const [page, setPage] = useState(0);
  const [metadata, setMetadata] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [jobResult, setJobResult] = useState(null);
  const [backupError, setBackupError] = useState('');
  const [modelsRevision, setModelsRevision] = useState(0);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [modelsError, setModelsError] = useState('');
  const requestInFlight = useRef(false);
  const [pendingRequest, setPendingRequest] = useState(() => {
    try {return readPendingBackupRequest(sessionStorage);} catch {return null;}
  });

  async function refreshHistory() {
    const result = await managementCommand('model-downloads', 'backup-verify-history', {});
    if (!Array.isArray(result.records)) throw new Error('검증 이력 응답이 올바르지 않습니다.');
    setJobs(result.records);
  }

  useEffect(() => {
    const controller = new AbortController();
    setModelsLoading(true);
    managementCommand('model-downloads', 'backup-models', {}, {signal: controller.signal}).then(result => {
      if (!Array.isArray(result.models)) throw new Error('모델 목록 응답이 올바르지 않습니다.');
      if (!controller.signal.aborted) {
        setModels(result.models);
        setModelsError('');
        setBackupError(result.backup_error || '');
        setSelected(previous => result.models.some(model => model.name === previous) ? previous : (result.models[0]?.name || ''));
      }
    }).catch(problem => {if (!controller.signal.aborted) setModelsError(problem.message || '모델 목록을 조회하지 못했습니다.');})
      .finally(() => {if (!controller.signal.aborted) setModelsLoading(false);});
    return () => controller.abort();
  }, [modelsRevision]);

  useEffect(() => {
    const controller = new AbortController();
    refreshHistory().catch(problem => {if (!controller.signal.aborted) setError(problem.message);});
    return () => controller.abort();
  }, []);

  async function compare() {
    setBusy(true); setError(''); setComparison(null);
    try {
      const result = await managementCommand('model-downloads', 'backup-compare', {model: selected, target});
      if (!Array.isArray(result.files)) throw new Error('비교 결과가 올바르지 않습니다.');
      setComparison(result); setFilter('all'); setPage(0);
    } catch (problem) {setError(problem.message || '비교하지 못했습니다.');}
    finally {setBusy(false);}
  }

  async function showMetadata() {
    setBusy(true); setError(''); setMetadata(null);
    try {setMetadata(await managementCommand('model-downloads', 'backup-metadata', {model: selected}));}
    catch (problem) {setError(problem.message || '메타정보를 조회하지 못했습니다.');}
    finally {setBusy(false);}
  }

  async function submitRequest(request) {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    setBusy(true); setError('');
    try {
      const result = validateBackupReceipt(request, await managementCommand('model-downloads', request.command, request.payload));
      setJobResult(result);
      setPendingRequest(null);
      try {sessionStorage.removeItem('model-backup-pending');} catch {}
      try {await refreshHistory();} catch {setError('접수는 확인됐지만 작업 이력을 새로고침하지 못했습니다.');}
    } catch (problem) {setError((problem.message || '접수 결과를 확인하지 못했습니다.') + ' 같은 요청 ID로 다시 확인하세요.');}
    finally {requestInFlight.current = false; setBusy(false);}
  }

  function beginRequest(command) {
    if (requestInFlight.current || busy || pendingRequest) return;
    try {
      const requestId = crypto.randomUUID().replaceAll('-', '');
      const payload = {model: selected, request_id: requestId};
      if (command === 'backup-verify') payload.target = target;
      const request = {command, payload};
      sessionStorage.setItem('model-backup-pending', JSON.stringify(request));
      setPendingRequest(request);
      submitRequest(request);
    } catch {setError('안전한 요청 ID를 저장할 수 없습니다. 브라우저 저장소를 확인하세요.');}
  }

  async function showJob(jobId) {
    setBusy(true); setError('');
    try {
      const result = await managementCommand('model-downloads', 'backup-verify-status', {job_id: jobId});
      setJobResult(result);
      if (Array.isArray(result.result?.files)) {setComparison(result.result); setFilter('all'); setPage(0);}
      await refreshHistory();
    } catch (problem) {setError(problem.message || '검증 결과를 조회하지 못했습니다.');}
    finally {setBusy(false);}
  }

  const pageSize = 100;
  const resultPage = modelBackupPage(comparison?.files || [], filter, page, pageSize);
  const selectedModel = models.find(model => model.name === selected);
  const localMissing = selectedModel?.local_present === false;

  return <section><h2>모델 백업 비교</h2>
    <p>크기와 수정 시각을 비교합니다. 내용의 해시 검증은 별도로 필요합니다. 진행 중인 백업은 결과에 반영될 수 있습니다.</p>
    {error && <p role="alert">{error}</p>}
    {modelsError && <p role="alert">{modelsError} {models.length > 0 && '아래 목록은 마지막 조회 결과입니다. 다시 조회해 주세요.'}</p>}
    {backupError && <p role="status">{backupError} 로컬 모델 목록과 메타정보는 조회할 수 있습니다.</p>}
    <button type="button" disabled={modelsLoading || busy} onClick={() => {setError(''); setComparison(null); setMetadata(null); setModelsRevision(value => value + 1);}}>{modelsLoading ? '모델 목록 조회 중…' : '모델과 백업 목록 새로고침'}</button>
    {modelsLoading && <p role="status">모델과 백업 목록을 확인하고 있습니다.</p>}
    <label>모델 디렉터리 <select value={selected} onChange={event => {setSelected(event.target.value); setComparison(null); setMetadata(null);}} disabled={busy || modelsLoading || !!modelsError || !models.length}>
      {models.map(model => <option key={model.name} value={model.name}>{model.name}{model.local_present === false ? ' · 백업만 있음' : model.backup_present === null ? ' · 백업 확인 불가' : model.backup_present ? '' : ' · 기존 공유 디렉터리 없음'}</option>)}
    </select></label>
    <label>비교 대상 <select value={target} disabled={busy} onChange={event => {setTarget(event.target.value); setComparison(null);}}>
      <option value="canonical">기존 공유 디렉터리</option>
      <option value="latest_snapshot">가장 최근 완료 스냅샷</option>
      <option value="snapshot_manifest">스냅샷 자체 무결성</option>
    </select></label>
    {target === 'latest_snapshot' && <p>스냅샷의 수정 시각은 복사 시각일 수 있습니다. 파일 내용은 SHA-256 검증으로 확인하세요.</p>}
    {target === 'snapshot_manifest' && <p>스냅샷의 현재 파일을 백업 당시 기록된 해시와 비교합니다. 공급처 원본 인증은 별도입니다.</p>}
    {localMissing && <p>로컬 모델이 없어 원본과 비교하거나 새 백업을 만들 수 없습니다. 완료된 스냅샷은 자체 무결성을 검증할 수 있습니다.</p>}
    <button type="button" onClick={compare} disabled={busy || modelsLoading || !!modelsError || !!backupError || !selected || localMissing || target === 'snapshot_manifest'}>{busy ? '비교 중…' : '백업과 비교'}</button>
    <button type="button" onClick={showMetadata} disabled={busy || modelsLoading || !!modelsError || !selected}>모델 메타정보</button>
    <button type="button" onClick={() => beginRequest('backup-verify')} disabled={busy || modelsLoading || !!modelsError || !!backupError || !selected || (localMissing && target !== 'snapshot_manifest') || !!pendingRequest}>SHA-256 검증 시작</button>
    <button type="button" onClick={() => beginRequest('backup-sync')} disabled={busy || modelsLoading || !!modelsError || !!backupError || !selected || localMissing || !!pendingRequest}>선택한 모델 백업</button>
    {!selected && <p>모델 목록을 불러온 뒤 디렉터리를 선택하세요. 목록 조회에 실패했다면 백업 연결을 확인하고 페이지를 다시 여세요.</p>}
    {busy && <p role="status">요청을 처리하고 있습니다. 완료된 뒤 다시 선택할 수 있습니다.</p>}
    {pendingRequest && <div role="status"><p>{pendingRequest.payload.model} 접수 확인 필요 · {pendingRequest.payload.request_id}</p>
      <p>확인을 중단해도 서버에서 이미 접수된 작업은 계속될 수 있습니다. 이력에서 상태를 확인하세요.</p>
      <button type="button" disabled={busy} onClick={() => submitRequest(pendingRequest)}>같은 요청 확인</button>
      <button type="button" disabled={busy} onClick={() => {try {sessionStorage.removeItem('model-backup-pending'); setPendingRequest(null);} catch {setError('브라우저 저장소를 확인하세요.');}}}>접수 확인 중단</button>
    </div>}
    <button type="button" onClick={() => refreshHistory().catch(problem => setError(problem.message))}>검증 이력 새로고침</button>
    <p>백업은 최신 스냅샷과 SHA-256을 비교하고 동일하면 재사용합니다. 변경된 경우 모델 전체를 새 스냅샷으로 복사하므로 모델 크기만큼 추가 공간이 필요합니다.</p>
    <p>검증은 선택한 파일을 전체적으로 읽으므로 시간이 오래 걸립니다. 작업 완료와 모든 파일의 일치는 별도입니다.</p>
    {metadata && <div><p>{metadata.origin === 'backup_snapshot' ? `백업 스냅샷 ${metadata.snapshot_id} · ` : metadata.origin === 'backup_directory' ? '기존 백업 디렉터리 · ' : ''}관련 서비스 · {metadata.services?.join(', ') || '확인된 등록 없음'} · 기존 매니페스트 {metadata.manifest_state}</p>
      <p>매니페스트의 해시는 선언값입니다. 파일 내용을 검증한 결과와 구분합니다.</p>
      <ul>{metadata.declared_sources?.map((item, index) => <li key={index}>{item.repository} · {item.revision}</li>)}</ul>
      <ul>{metadata.declared_files?.slice(0, 200).map((item, index) => <li key={index}>{item.path} · {item.sha256}</li>)}</ul>
      {metadata.declared_files?.length > 200 && <p>선언 파일은 처음 200개만 표시합니다.</p>}
    </div>}
    {jobs.length > 0 && <ul>{jobs.map(job => <li key={job.job_id}>{job.model} · {job.operation === 'sync' ? '백업' : '검증'} · {job.status}{job.stage && ` · ${job.stage}`}{job.current_file && ` · ${job.current_file}`}{Number.isFinite(job.file_bytes) ? ` · 현재 파일 ${job.file_bytes.toLocaleString()} / ${job.file_total_bytes?.toLocaleString() ?? '?'}바이트` : Number.isFinite(job.bytes) ? ` · ${job.bytes.toLocaleString()} / ${job.total_bytes?.toLocaleString() ?? '?'}바이트` : ''} <button type="button" disabled={busy} onClick={() => showJob(job.job_id)}>상태·결과 확인</button></li>)}</ul>}
    {jobResult && <p role="status">{jobResult.model} · {jobResult.status}{jobResult.error && ' · ' + jobResult.error}{jobResult.operation === 'sync' && jobResult.result && ` · ${jobResult.result.file_count}개 파일 SHA-256 확인 · ${jobResult.result.reused ? '기존 스냅샷 재사용' : '새 스냅샷 저장'}`}</p>}
    {comparison && <div><p role="status">{comparison.model} · {comparison.complete ? '목록 조회 완료' : '일부 경로 확인 실패'} · 파일 {comparison.files.length.toLocaleString()}개</p>
      <p>대상 · {comparison.target === 'snapshot_manifest' ? `스냅샷 ${comparison.snapshot_id} 자체 무결성` : comparison.target === 'latest_snapshot' ? `스냅샷 ${comparison.snapshot_id}` : '기존 공유 디렉터리'}</p>
      {comparison.note && <p>{comparison.note}</p>}
      <p>비교 기준 · {comparison.comparison_basis === 'sha256' ? 'SHA-256' : '크기·수정 시각'}</p>
      {comparison.source_errors?.map((item, index) => <p key={'source'+index}>원본 {item.path} · {item.reason}</p>)}
      {comparison.backup_errors?.map((item, index) => <p key={'backup'+index}>백업 {item.path} · {item.reason}</p>)}
      <label>상태 필터 <select value={filter} onChange={event => {setFilter(event.target.value); setPage(0);}}>
        <option value="all">전체 · {comparison.files.length.toLocaleString()}개</option>
        {Object.entries(resultPage.counts).map(([status, count]) => <option key={status} value={status}>{labels[status] || status} · {count.toLocaleString()}개</option>)}
      </select></label>
      {resultPage.total === 0 ? <p>해당하는 파일이 없습니다.</p> : <>
        <p>{(resultPage.page * pageSize + 1).toLocaleString()}–{Math.min((resultPage.page + 1) * pageSize, resultPage.total).toLocaleString()} / {resultPage.total.toLocaleString()}개</p>
        <ul>{resultPage.files.map(item => <li key={item.path}>{item.path} · {labels[item.status] || item.status}</li>)}</ul>
        <button type="button" disabled={resultPage.page === 0} onClick={() => setPage(resultPage.page - 1)}>이전 파일</button>
        <button type="button" disabled={(resultPage.page + 1) * pageSize >= resultPage.total} onClick={() => setPage(resultPage.page + 1)}>다음 파일</button>
      </>}
    </div>}
  </section>;
}
