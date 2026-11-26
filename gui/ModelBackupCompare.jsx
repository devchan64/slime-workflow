import React, {useEffect, useId, useRef, useState} from 'react';
import {managementCommand, untilAborted} from './managementCommand.js';
import {requestErrorMessage} from './requestError.mjs';
import {readPendingBackupRequest, validateBackupReceipt} from './modelBackupPending.mjs';
import {backupDirectories, modelBackupPage, verificationSummary, validBackupJob, validBackupComparison, validBackupMetadata, validBackupModels, backupActionReasons} from './modelBackupResults.mjs';
import {validCatalogHistory} from './modelCatalogSearch.mjs';

const labels = {missing: '백업 누락', different: '차이 있음', matches_metadata: '크기·시간 일치', verified: 'SHA-256 일치', backup_only: '백업에만 있음', unknown: '확인 불가'};
const jobLabels = {running: '진행 중', completed: '완료', failed: '실패', interrupted: '중단됨'};
const presence = value => value === true ? '있음' : value === false ? '없음' : '확인 불가';
const targets = {canonical: '기존 공유 디렉터리', latest_snapshot: '가장 최근 완료 스냅샷', snapshot_manifest: '스냅샷 자체 무결성', legacy: '이관 전 공유 디렉터리'};
const legacyModels = new Set(['catalog-flux-report-vision', 'catalog-trellis-dinov2', 'catalog-trellis-image-large', 'catalog-hermes-coding', 'catalog-writer-agent', 'catalog-translation-model', 'catalog-heartmula', 'catalog-dasheng-audiogen', 'catalog-minimax-hf-cache']);
const directoryLabel = (name, relativePath) => relativePath ? `${relativePath} · 개별 백업 대상` : ({'catalog-flux-report-vision': 'models/flux-report-vision · 개별 모델', 'catalog-trellis-dinov2': 'models/trellis-dinov2 · 개별 모델', 'catalog-trellis-image-large': 'models/trellis-image-large · 개별 모델', 'catalog-hermes-coding': 'models/hermes-coding · 개별 모델', 'catalog-writer-agent': 'models/qwen3-embedding-0.6b · 개별 모델', 'catalog-translation-model': 'models/translategemma-4b · 개별 모델', 'catalog-heartmula': 'models/audio/heartmula · 음악 모델', 'catalog-dasheng-audiogen': 'models/audio/dasheng-audiogen · 효과음 모델', 'catalog-minimax-hf-cache': 'cache/huggingface · 캐시'}[name] || name);
function jobTime(value) {const time = new Date(value); return value && Number.isFinite(time.getTime()) ? time.toLocaleString('ko-KR') : '시작 시각 확인 불가';}
function jobSummary(job) {return `${job.model} · ${jobLabels[job.status] || job.status} · 작업 ID ${job.job_id}${job.error ? ' · ' + job.error : ''}${job.operation === 'sync' && job.result ? ` · ${job.result.file_count}개 파일 SHA-256 확인 · ${job.result.reused ? '기존 스냅샷 재사용' : '새 스냅샷 저장'}` : ''}`;}

export default function ModelBackupCompare({requestedSelection}) {
  const actionReasonId=useId(),modelsLoadingId=useId(),busyId=useId(),historyLoadingId=useId();
  const [models, setModels] = useState([]);
  const [selected, setSelected] = useState('');
  const [selectionNeedsConfirmation,setSelectionNeedsConfirmation]=useState(false);
  const [modelQuery, setModelQuery] = useState('');
  const [target, setTarget] = useState('canonical');
  const [comparison, setComparison] = useState(null);
  const [comparisonOrigin, setComparisonOrigin] = useState(null);
  const [filter, setFilter] = useState('all');
  const [fileQuery, setFileQuery] = useState('');
  const [directory, setDirectory] = useState('');
  const [page, setPage] = useState(0);
  const [metadata, setMetadata] = useState(null);
  const [metadataCheckedAt,setMetadataCheckedAt]=useState(null);
  const [error, setError] = useState('');
  const [historyError, setHistoryError] = useState('');
  const [busy, setBusy] = useState(false);
  const [jobs, setJobs] = useState(null);
  const [historyCheckedAt,setHistoryCheckedAt]=useState(null);
  const [selectedHistoryOnly, setSelectedHistoryOnly] = useState(false);
  const [jobResult, setJobResult] = useState(null);
  const [shownJobId, setShownJobId] = useState(null);
  const [loadingJobId,setLoadingJobId]=useState(null);
  const [failedJobId, setFailedJobId] = useState(null);
  const [backupError, setBackupError] = useState('');
  const [modelsRevision, setModelsRevision] = useState(0);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [modelsError, setModelsError] = useState('');
  const modelsRequestInFlight = useRef(true);
  const requestInFlight = useRef(false);
  const historyRevision = useRef(0);
  const historyRequest = useRef(null);
  const jobReadRequest = useRef(null);
  const compareRequest = useRef(null);
  const [comparisonLoading,setComparisonLoading]=useState(false);
  const metadataRequest = useRef(null);
  const [metadataLoading,setMetadataLoading]=useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const handledSelection = useRef(null), headingRef = useRef(null), searchRef = useRef(null), fileSearchRef = useRef(null), folderHeadingRef = useRef(null);
  const [selectionNotice, setSelectionNotice] = useState('');
  const [pendingRequest, setPendingRequest] = useState(() => {
    try {return readPendingBackupRequest(sessionStorage);} catch {return null;}
  });

  useEffect(() => {
    if (target === 'legacy' && !legacyModels.has(selected)) setTarget('canonical');
  }, [selected, target]);

  useEffect(() => {setDirectory('');}, [comparison]);

  async function refreshHistory(signal) {
    const revision = ++historyRevision.current;
    try {
      const request = managementCommand('model-downloads', 'backup-verify-history', {}, {signal});
      const result = signal ? await untilAborted(request, signal) : await request;
      if (revision !== historyRevision.current) return;
      if (!validCatalogHistory(result)) throw new Error('검증 이력 응답이 올바르지 않습니다.');
      setJobs(result.records);setHistoryCheckedAt(new Date());
      setHistoryError('');
    } catch (problem) {
      if (revision === historyRevision.current) throw problem;
    }
  }

  async function reloadHistory() {
    if (historyRequest.current) return;
    const controller = new AbortController(); historyRequest.current = controller;
    let timedOut = false;
    const timeout = setTimeout(() => {timedOut = true; controller.abort();}, 30000);
    setHistoryLoading(true); setHistoryError('');
    try {await refreshHistory(controller.signal);}
    catch (problem) {if (historyRequest.current === controller) setHistoryError(timedOut ? '이력 조회 시간이 초과됐습니다. 다시 시도하세요.' : `이력을 새로고침하지 못했습니다. ${requestErrorMessage(problem)}`);}
    finally {clearTimeout(timeout); if (historyRequest.current === controller) {historyRequest.current = null; setHistoryLoading(false);}}
  }

  useEffect(() => {
    const controller = new AbortController();
    let active = true, timedOut = false;
    const timeout = setTimeout(() => {timedOut = true; controller.abort();}, 30000);
    modelsRequestInFlight.current = true;
    setModelsLoading(true);
    untilAborted(managementCommand('model-downloads', 'backup-models', {}, {signal: controller.signal}), controller.signal).then(result => {
      if (!validBackupModels(result)) throw new Error('모델 목록 응답이 올바르지 않습니다.');
      if (!controller.signal.aborted) {
        if (selected && !result.models.some(model => model.name === selected)) {setComparison(null); setMetadata(null); setSelectionNeedsConfirmation(true); setSelectionNotice(`이전에 선택한 ${selected} 디렉터리가 새 목록에 없어 선택을 변경했습니다. 대상을 다시 확인하세요.`);}
        setModels(result.models);
        setModelsError('');
        setBackupError(result.backup_error || '');
        setSelected(previous => result.models.some(model => model.name === previous) ? previous : (result.models[0]?.name || ''));
      }
    }).catch(problem => {if (active) setModelsError(timedOut ? '모델 목록 조회 시간이 초과됐습니다. 다시 조회하세요.' : `모델 목록을 조회하지 못했습니다. ${requestErrorMessage(problem)}`);})
      .finally(() => {clearTimeout(timeout); if (active) {modelsRequestInFlight.current = false; setModelsLoading(false);}});
    return () => {active = false; clearTimeout(timeout); controller.abort();};
  }, [modelsRevision]);

  useEffect(() => {
    if (!requestedSelection || handledSelection.current === requestedSelection || busy || modelsLoading) return;
    if (document.activeElement===document.body || document.activeElement===requestedSelection.focusAtStart) {
      headingRef.current?.scrollIntoView({block: 'start'});
      headingRef.current?.focus();
    }
    if (modelsError || !models.some(model => model.name === requestedSelection.name)) {
      setSelectionNotice('선택한 설치본을 백업 목록에서 확인할 수 없습니다. 목록을 새로고침하세요.');
      return;
    }
    handledSelection.current = requestedSelection;
    setSelectionNotice(''); setSelectionNeedsConfirmation(false); setSelected(requestedSelection.name); setModelQuery('');
    setComparison(null); setMetadata(null); setJobResult(null);
    if (requestedSelection.jobId) showJob(requestedSelection.jobId);
  }, [requestedSelection, busy, modelsLoading, modelsError, models]);

  useEffect(() => {
    reloadHistory();
    return () => {historyRevision.current++; const request = historyRequest.current; historyRequest.current = null; request?.abort(); const jobRequest = jobReadRequest.current; jobReadRequest.current = null; jobRequest?.abort(); const comparisonRequest=compareRequest.current;compareRequest.current=null;comparisonRequest?.abort();const metadataRead=metadataRequest.current;metadataRequest.current=null;metadataRead?.abort();};
  }, []);

  async function compare(event) {
    if(compareRequest.current)return;
    const origin=event?.currentTarget,restoreFocus=origin && document.activeElement===origin;
    const controller=new AbortController();compareRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setComparisonLoading(true);setError('');
    try {
      const result = await untilAborted(managementCommand('model-downloads', 'backup-compare', {model: selected, target},{signal:controller.signal}),controller.signal);
      if(compareRequest.current!==controller)return;
      if (!validBackupComparison(result,selected,target)) throw new Error('비교 결과의 대상 또는 형식을 확인할 수 없습니다.');
      setJobResult(null);setComparison(result); setComparisonOrigin({kind: 'comparison', time: new Date().toISOString()}); setFilter('all'); setFileQuery(''); setPage(0);
    } catch (problem) {if(compareRequest.current===controller)setError((timedOut ? '비교 조회 시간이 초과됐습니다. 다시 시도하세요.' : requestErrorMessage(problem))+(comparison ? ' 이전 비교 결과를 유지합니다.' : ''));}
    finally {clearTimeout(timeout);if(compareRequest.current===controller){compareRequest.current=null;setComparisonLoading(false);setBusy(false);if(restoreFocus)requestAnimationFrame(()=>{if(document.activeElement===document.body && origin.isConnected && !origin.disabled)origin.focus();});}}
  }

  async function showMetadata(event) {
    if(metadataRequest.current)return;
    const origin=event?.currentTarget,restoreFocus=origin && document.activeElement===origin;
    const controller=new AbortController();metadataRequest.current=controller;let timedOut=false;
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    setBusy(true);setMetadataLoading(true);setError('');
    try {
      const result=await untilAborted(managementCommand('model-downloads','backup-metadata',{model:selected},{signal:controller.signal}),controller.signal);
      if(metadataRequest.current!==controller)return;
      if(!validBackupMetadata(result,selected))throw new Error('메타정보 대상 또는 형식을 확인할 수 없습니다.');
      setMetadata(result);setMetadataCheckedAt(new Date());
    } catch(problem) {if(metadataRequest.current===controller)setError((timedOut ? '메타정보 조회 시간이 초과됐습니다. 다시 시도하세요.' : requestErrorMessage(problem))+(metadata ? ' 이전 메타정보를 유지합니다.' : ''));}
    finally {clearTimeout(timeout);if(metadataRequest.current===controller){metadataRequest.current=null;setMetadataLoading(false);setBusy(false);if(restoreFocus)requestAnimationFrame(()=>{if(document.activeElement===document.body && origin.isConnected && !origin.disabled)origin.focus();});}}
  }

  async function submitRequest(request) {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    setBusy(true); setError('');
    try {
      const result = validateBackupReceipt(request, await managementCommand('model-downloads', request.command, request.payload));
      setShownJobId(null);
      setJobResult(result);
      setPendingRequest(null);
      try {sessionStorage.removeItem('model-backup-pending');} catch {}
      try {await refreshHistory();} catch {setHistoryError('접수는 확인됐지만 작업 이력을 새로고침하지 못했습니다.');}
    } catch (problem) {setError((problem?.message ? requestErrorMessage(problem) : '접수 결과를 확인하지 못했습니다.') + ' 같은 요청 ID로 다시 확인하세요.');}
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
    if (jobReadRequest.current) return;
    const controller = new AbortController(); jobReadRequest.current = controller;
    let timedOut = false;
    const timeout = setTimeout(() => {timedOut = true; controller.abort();}, 30000);
    setBusy(true); setLoadingJobId(jobId); setError(''); setFailedJobId(null);
    try {
      const result = await untilAborted(managementCommand('model-downloads', 'backup-verify-status', {job_id: jobId}, {signal: controller.signal}), controller.signal);
      if (jobReadRequest.current !== controller) return;
      if (!validBackupJob(result,jobId)) throw new Error('작업 결과의 형식 또는 작업 ID를 확인할 수 없습니다.');
      setJobResult(result);
      setShownJobId(jobId);
      setComparisonOrigin({kind: 'history', time: result.finished_at || result.started_at || null});
      setComparison(Array.isArray(result.result?.files) ? result.result : null); setFilter('all'); setFileQuery(''); setPage(0);
      try {await refreshHistory(controller.signal);} catch {if (jobReadRequest.current === controller) setHistoryError('작업 결과는 조회했지만 이력을 새로고침하지 못했습니다. 이력 새로고침을 다시 시도하세요.');}
    } catch (problem) {if (jobReadRequest.current === controller) {setFailedJobId(jobId); setError(`작업 ID ${jobId} · `+(timedOut ? '작업 결과 조회 시간이 초과됐습니다. 다시 시도하세요.' : `작업 결과를 조회하지 못했습니다. ${requestErrorMessage(problem)}`));}}
    finally {clearTimeout(timeout); if (jobReadRequest.current === controller) {jobReadRequest.current = null; setLoadingJobId(null); setBusy(false);}}
  }

  const pageSize = 100;
  const allFiles = comparison?.files || [];
  const directories = backupDirectories(allFiles, directory);
  const scopedFiles = allFiles.filter(item => !directory || item.path.startsWith(`${directory}/`));
  const resultPage = modelBackupPage(scopedFiles.filter(item => item.path.toLocaleLowerCase().includes(fileQuery.trim().toLocaleLowerCase())), filter, page, pageSize);
  const selectedModel = models.find(model => model.name === selected);
  const searchTerms = modelQuery.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const visibleJobs = jobs ? (selectedHistoryOnly ? jobs.filter(job => job.model === selected) : jobs) : [];
  const previousHistoryMessage = jobs ? visibleJobs.length ? ' 아래는 마지막 조회 결과입니다.' : selectedHistoryOnly && jobs.length ? ' 마지막 조회에서 선택한 디렉터리의 이력이 없었습니다.' : ' 마지막 조회에서 이력이 없었습니다.' : '';
  const matchingModels = models.filter(model => searchTerms.every(term => `${model.name} ${directoryLabel(model.name, model.relative_path)}`.toLocaleLowerCase().includes(term)));
  const localMissing = selectedModel?.local_present === false;
  const {compare:compareReason,metadata:metadataReason,verify:verifyReason,sync:syncReason}=backupActionReasons({busy,modelsLoading,modelsError,backupError,selected,localMissing,target,pendingRequest,selectionNeedsConfirmation});
  const actionReasons=[...new Set([compareReason,metadataReason,verifyReason,syncReason].filter(Boolean))];
  const reasonDescription=reason=>reason ? `${actionReasonId}-${actionReasons.indexOf(reason)}` : undefined;

  return <section className="model-backup"><h2 ref={headingRef} tabIndex={-1}>모델 백업 비교</h2>
    {jobResult && <p role="status">{failedJobId && error ? '이전 조회 결과 · ' : ''}{jobSummary(jobResult)}</p>}
    {selectionNotice && <p role="alert">{selectionNotice}</p>}
    <p>크기와 수정 시각을 비교합니다. 내용의 해시 검증은 별도로 필요합니다. 진행 중인 백업은 결과에 반영될 수 있습니다.</p>
    {error && <p role="alert">{error}</p>}
    {modelsError && <p role="alert">{modelsError}{models.length > 0 && ' 아래 목록은 마지막 조회 결과입니다.'}</p>}
    {backupError && <p role="status">{backupError} 로컬 모델 목록과 메타정보는 조회할 수 있습니다.</p>}
    <button type="button" aria-disabled={modelsLoading || busy} aria-describedby={modelsLoading ? modelsLoadingId : busy ? busyId : undefined} onClick={() => {if (modelsRequestInFlight.current || busy) return; modelsRequestInFlight.current = true; setError(''); setModelsRevision(value => value + 1);}}>{modelsLoading ? '모델 목록 조회 중…' : '모델과 백업 목록 새로고침'}</button>
    {modelsLoading && <p id={modelsLoadingId} role="status">모델과 백업 목록을 확인하고 있습니다.{models.length > 0 && ' 아래는 마지막 조회 결과입니다.'}</p>}
    {(modelsLoading || modelsError) && (comparison || metadata) && <p role="status">비교·메타정보는 마지막으로 확인한 결과입니다. 모델 목록 확인 후 다시 조회하세요.</p>}
    <h3>1. 대상 선택</h3>
    <p>로컬 모델 폴더와 Samba 백업의 최상위 디렉터리입니다. 아래 목록에서 비교할 디렉터리를 선택하세요.</p>
    <label>디렉터리 검색 <input ref={searchRef} type="search" value={modelQuery} onChange={event => setModelQuery(event.target.value)} placeholder="예: flux, wan22, kimodo"/></label>
    {modelQuery && <button type="button" onClick={() => {setModelQuery(''); searchRef.current?.focus();}}>디렉터리 검색 지우기</button>}
    {selectedModel && <p>선택한 디렉터리 · <strong>{directoryLabel(selectedModel.name, selectedModel.relative_path)}</strong>{selectionNeedsConfirmation && ' · 직접 선택 확인 필요'} · 로컬 {presence(selectedModel.local_present)} · 기존 공유 {presence(selectedModel.backup_present)} · 완료 스냅샷 {presence(selectedModel.snapshot_present)}</p>}
    {selectedModel?.included_targets?.length > 0 && <p>이 폴더에는 개별 백업 대상 {selectedModel.included_targets.map(name => directoryLabel(name)).join(', ')}이 포함됩니다. 전체 폴더와 개별 대상을 각각 백업하면 내용이 여러 스냅샷에 저장됩니다.</p>}
    {selectedModel?.parent_target && <p>이 설치본은 상위 백업 대상 {selectedModel.parent_target}에도 포함됩니다. 각각 백업하면 내용이 여러 스냅샷에 저장됩니다.</p>}
    {selectedModel?.equivalent_target && <p>백업 대상 {selectedModel.equivalent_target}은 같은 디렉터리입니다. 각각 백업하면 내용이 여러 스냅샷에 저장됩니다.</p>}
    {(models.length > 0 || (!modelsLoading && !modelsError)) && <p role="status">{modelQuery.trim() ? `검색 결과 ${matchingModels.length}개 / 전체 ${models.length}개` : `디렉터리 ${models.length}개`}{searchTerms.length > 0 && selected && !matchingModels.some(model => model.name === selected) ? ' · 현재 선택은 유지됩니다.' : ''}</p>}
    {matchingModels.length > 0 && <div role="group" aria-label="백업 모델 디렉터리 목록" className="model-choice-list">
      {matchingModels.map(model => <button key={model.name} type="button" className="generator-history-select" aria-pressed={selected === model.name} disabled={busy || modelsLoading || !!modelsError} onClick={() => {handledSelection.current = requestedSelection; setSelectionNotice(''); setSelectionNeedsConfirmation(false); setSelected(model.name); setComparison(null); setMetadata(null); setJobResult(null);}}><span className="history-card-content"><span className="history-card-heading"><strong>{directoryLabel(model.name, model.relative_path)}</strong>{selected === model.name && <span>{selectionNeedsConfirmation ? '선택 확인 필요' : '선택됨'}</span>}</span><small className="history-card-summary">로컬 {presence(model.local_present)} · 기존 공유 {presence(model.backup_present)} · 완료 스냅샷 {presence(model.snapshot_present)}</small></span></button>)}
    </div>}
    {modelQuery.trim() && matchingModels.length === 0 && !modelsLoading && !modelsError && <p>일치하는 디렉터리가 없습니다. 다른 이름으로 검색하세요.</p>}
    <p>‘기존 공유’는 현재 복사된 공유 폴더이며, ‘완료 스냅샷’은 이 관리 기능으로 별도 저장한 백업입니다. 있음은 파일 내용이 일치한다는 뜻이 아닙니다.</p>
    <p>스냅샷은 Samba 백업 경로의 숨김 폴더 <code>.model-backup-snapshots/모델/작업ID</code>에 저장됩니다. 파일 관리자에서 숨김 파일을 표시해야 볼 수 있습니다. 복사·검증 중에는 <code>.pending-작업ID</code> 폴더에 있으며 완료 후 작업 ID 폴더로 게시됩니다.</p>
    <p>스냅샷 백업은 모델 루트 안의 심볼릭 링크를 따라 대상 파일을 복사합니다. 링크 자체와 공유 관계는 보존하지 않으므로 복원 시 중복 용량이 생길 수 있습니다.</p>
    <label>비교 대상 <select value={target} disabled={busy} onChange={event => {setTarget(event.target.value); setComparison(null);}}>
      <option value="canonical">기존 공유 디렉터리</option>
      <option value="legacy" disabled={!legacyModels.has(selected)}>이관 전 공유 디렉터리</option>
      <option value="latest_snapshot">가장 최근 완료 스냅샷</option>
      <option value="snapshot_manifest">스냅샷 자체 무결성</option>
    </select></label>
    {target === 'latest_snapshot' && <p>스냅샷의 수정 시각은 복사 시각일 수 있습니다. 파일 내용은 SHA-256 검증으로 확인하세요.</p>}
    {target === 'legacy' && <p>새 설치본을 이전 이름으로 저장된 공유 디렉터리와 비교합니다. 이관 후 새 경로가 백업되었다는 뜻은 아닙니다.</p>}
    {target === 'snapshot_manifest' && <p>스냅샷의 현재 파일을 백업 당시 기록된 해시와 비교합니다. 공급처 원본 인증은 별도입니다.</p>}
    {localMissing && <p>로컬 모델이 없어 원본과 비교하거나 새 백업을 만들 수 없습니다. 완료된 스냅샷은 자체 무결성을 검증할 수 있습니다.</p>}
    <h3>2. 비교 및 백업</h3>
    {selectedModel && <p>비교·검증 대상 · <strong>{directoryLabel(selectedModel.name, selectedModel.relative_path)}</strong> · {targets[target]} · 백업은 별도 스냅샷으로 저장됩니다.</p>}
    <div className="generator-history-actions">
    <button type="button" onClick={compare} disabled={Boolean(compareReason)} aria-describedby={reasonDescription(compareReason)}>백업과 비교</button>
    <button type="button" onClick={showMetadata} disabled={Boolean(metadataReason)} aria-describedby={reasonDescription(metadataReason)}>모델 메타정보</button>
    <button type="button" onClick={() => beginRequest('backup-verify')} disabled={Boolean(verifyReason)} aria-describedby={reasonDescription(verifyReason)}>SHA-256 검증 시작</button>
    <button type="button" onClick={() => beginRequest('backup-sync')} disabled={Boolean(syncReason)} aria-describedby={reasonDescription(syncReason)}>선택한 모델 백업</button>
    </div>
    {actionReasons.map((reason,index)=><p key={reason} id={`${actionReasonId}-${index}`}>{reason}</p>)}
    {target === 'snapshot_manifest' && <p>자체 무결성은 크기·시간 비교를 지원하지 않습니다. SHA-256 검증을 시작하세요.</p>}
    {!selected && <p>모델 목록을 불러온 뒤 디렉터리를 선택하세요. 목록 조회에 실패했다면 백업 연결을 확인하고 페이지를 다시 여세요.</p>}
    {busy && <p id={busyId} role="status">요청을 처리하고 있습니다. 완료된 뒤 다시 선택할 수 있습니다.</p>}
    {pendingRequest && <div role="status"><p>{pendingRequest.payload.model} 접수 확인 필요 · {pendingRequest.payload.request_id}</p>
      <p>확인을 중단해도 서버에서 이미 접수된 작업은 계속될 수 있습니다. 이력에서 상태를 확인하세요.</p>
      <button type="button" disabled={busy} onClick={() => submitRequest(pendingRequest)}>같은 요청 확인</button>
      <button type="button" disabled={busy} onClick={() => {try {sessionStorage.removeItem('model-backup-pending'); setPendingRequest(null);} catch {setError('브라우저 저장소를 확인하세요.');}}}>접수 확인 중단</button>
    </div>}
    <p>백업은 최신 스냅샷과 SHA-256을 비교하고 동일하면 재사용합니다. 변경된 경우 모델 전체를 새 스냅샷으로 복사하므로 모델 크기만큼 추가 공간이 필요합니다.</p>
    <p>검증은 선택한 파일을 전체적으로 읽으므로 시간이 오래 걸립니다. 작업 완료와 모든 파일의 일치는 별도입니다.</p>
    {metadata && <div>{metadataLoading && <p role="status">메타정보를 다시 조회하고 있습니다. 아래는 마지막으로 확인한 결과입니다.</p>}{metadataCheckedAt && <p>메타정보 마지막 조회 성공 · <time dateTime={metadataCheckedAt.toISOString()}>{metadataCheckedAt.toLocaleString('ko-KR')}</time></p>}<p>{metadata.origin === 'backup_snapshot' ? `백업 스냅샷 ${metadata.snapshot_id} · ` : metadata.origin === 'backup_directory' ? '기존 백업 디렉터리 · ' : ''}관련 서비스 · {metadata.services?.join(', ') || '확인된 등록 없음'} · 기존 매니페스트 {metadata.manifest_state}</p>
      <p>매니페스트의 해시는 선언값입니다. 파일 내용을 검증한 결과와 구분합니다.</p>
      <ul>{metadata.declared_sources?.map((item, index) => <li key={index}>{item.repository} · {item.revision}</li>)}</ul>
      <ul>{metadata.declared_files?.slice(0, 200).map((item, index) => <li key={index}>{item.path} · {item.sha256}</li>)}</ul>
      {metadata.declared_files?.length > 200 && <p>선언 파일은 처음 200개만 표시합니다.</p>}
    </div>}
    <h3>3. 작업 상태와 이력</h3>
    {loadingJobId && <p role="status">작업 ID {loadingJobId}의 상태와 결과를 조회하고 있습니다.</p>}
    {historyError && <p role="alert">{historyError}{previousHistoryMessage}</p>}
    <button type="button" aria-disabled={historyLoading} aria-describedby={historyLoading ? historyLoadingId : undefined} onClick={reloadHistory}>{historyLoading ? '이력 조회 중…' : '백업·검증 이력 새로고침'}</button>
    {historyLoading && <p id={historyLoadingId} role="status">이력을 조회하고 있습니다.{previousHistoryMessage}</p>}
    {historyCheckedAt && <p>이력 마지막 조회 성공 · <time dateTime={historyCheckedAt.toISOString()}>{historyCheckedAt.toLocaleString('ko-KR')}</time></p>}
    <p>이 이력은 이 화면과 게이트웨이에서 접수한 작업만 표시합니다. 외부 백업 진행률은 포함되지 않습니다.</p>
    <label><input type="checkbox" checked={selectedHistoryOnly} onChange={event => setSelectedHistoryOnly(event.target.checked)} disabled={!selected}/> 선택한 디렉터리의 이력만 보기</label>
    {jobs ? <><p role="status">최근 조회된 이력 {jobs.length}건 중 {visibleJobs.length}건 표시 · 오래된 이력은 이 목록에 없을 수 있습니다.</p>
    {visibleJobs.length > 0 ? <details><summary>최근 백업·검증 작업 {visibleJobs.length}건 보기</summary><ul>{visibleJobs.map(job => <li key={job.job_id}><strong>{job.model} · {job.operation === 'sync' ? '백업' : '검증'} · {jobLabels[job.status] || job.status}</strong><br/>시작 · {jobTime(job.started_at)} · {job.operation === 'sync' ? '스냅샷 백업' : (targets[job.target] || '기존 공유 디렉터리')} · 작업 ID {job.job_id}{job.stage && ` · ${job.stage}`}{job.current_file && ` · ${job.current_file}`}{Number.isFinite(job.file_bytes) ? ` · 현재 파일 ${job.file_bytes.toLocaleString()} / ${job.file_total_bytes?.toLocaleString() ?? '?'}바이트` : Number.isFinite(job.bytes) ? ` · ${job.bytes.toLocaleString()} / ${job.total_bytes?.toLocaleString() ?? '?'}바이트` : ''} <button type="button" aria-label={`${job.model} ${jobTime(job.started_at)} ${job.operation === 'sync' ? '백업' : '검증'} 상태·결과 확인`} aria-disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={() => {if (!busy) showJob(job.job_id);}}>상태·결과 확인</button>{jobResult && shownJobId === job.job_id && <p>{failedJobId === job.job_id && error ? '이전 조회 결과 · ' : ''}{jobSummary(jobResult)}</p>}{error && failedJobId === job.job_id && <p>{error}</p>}</li>)}</ul></details> : <p>{selectedHistoryOnly ? '최근 조회된 이력에 선택한 디렉터리의 작업이 없습니다.' : '최근 백업·검증 이력이 없습니다.'}</p>}</> : !historyLoading && <p>이력을 확인하지 못했습니다. 이력 새로고침을 시도하세요.</p>}
    {comparison && <div><h3>비교·검증 결과</h3>{comparisonLoading && <p role="status">비교를 다시 조회하고 있습니다. 아래는 마지막으로 확인한 결과입니다.</p>}<p role="status">{comparison.model} · {comparison.complete ? '목록 조회 완료' : '일부 경로 확인 실패'} · 파일 {comparison.files.length.toLocaleString()}개</p>
      {comparisonOrigin?.kind === 'history' && <p>이력의 과거 결과 · {jobTime(comparisonOrigin.time)} · 이후 파일이나 경로가 변경됐을 수 있습니다.</p>}
      {comparisonOrigin?.kind === 'comparison' && <p>비교 조회 시각 · {jobTime(comparisonOrigin.time)} · 이후 파일이나 경로가 변경됐을 수 있습니다.</p>}
      {comparison.model !== selected && <p>이 결과는 현재 선택한 디렉터리가 아닌 이전 작업의 결과입니다.</p>}
      <p>대상 · {comparison.target === 'snapshot_manifest' ? `스냅샷 ${comparison.snapshot_id} 자체 무결성` : comparison.target === 'latest_snapshot' ? `스냅샷 ${comparison.snapshot_id}` : targets[comparison.target] || '기존 공유 디렉터리'}</p>
      {comparison.note && <p>{comparison.note}</p>}
      <p>비교 기준 · {comparison.comparison_basis === 'sha256' ? 'SHA-256' : '크기·수정 시각'}</p>
      {verificationSummary(comparison) && <p role="status">전체 검증 결과 · {verificationSummary(comparison)}</p>}
      {comparison.comparison_basis !== 'sha256' && <p>크기나 수정 시각이 다르면 차이로 표시합니다. 내용이 다른지 확인하려면 SHA-256 검증을 실행하세요.</p>}
      <p>결과 요약{directory && ' · 선택 폴더와 하위 폴더'}{fileQuery.trim() && ' · 검색된 파일'} · {Object.entries(resultPage.counts).map(([status, count]) => `${labels[status] || status} ${count.toLocaleString()}개`).join(' · ') || '파일 없음'}</p>
      {comparison.source_errors?.map((item, index) => <p key={'source'+index}>원본 {item.path} · {item.reason}</p>)}
      {comparison.backup_errors?.map((item, index) => <p key={'backup'+index}>백업 {item.path} · {item.reason}</p>)}
      <h4 ref={folderHeadingRef} tabIndex={-1}>폴더별로 보기</h4>
      <p role="status">현재 폴더 · {directory || '최상위'} · 파일 목록은 하위 폴더를 포함합니다.</p>
      {directory && <button type="button" onClick={() => {setDirectory(directory.includes('/') ? directory.slice(0, directory.lastIndexOf('/')) : ''); setPage(0); folderHeadingRef.current?.focus();}}>상위 폴더로</button>}
      {directories.length > 0 && <ul>{directories.map(folder => <li key={folder.path}><button type="button" onClick={() => {setDirectory(folder.path); setPage(0); folderHeadingRef.current?.focus();}}>{folder.name} · 파일 {folder.count}개</button> · {Object.entries(folder.statuses).map(([status, count]) => `${labels[status] || status} ${count}개`).join(' · ')}</li>)}</ul>}
      <label>파일 경로 검색 <input ref={fileSearchRef} type="search" value={fileQuery} onChange={event => {setFileQuery(event.target.value); setFilter('all'); setPage(0);}} placeholder="파일명 또는 경로"/></label>
      {fileQuery && <button type="button" onClick={() => {setFileQuery(''); setFilter('all'); setPage(0); fileSearchRef.current?.focus();}}>파일 경로 검색 지우기</button>}
      <label>상태 필터 <select value={filter} onChange={event => {setFilter(event.target.value); setPage(0);}}>
        <option value="all">전체 · {Object.values(resultPage.counts).reduce((sum, count) => sum + count, 0).toLocaleString()}개</option>
        {Object.entries(resultPage.counts).map(([status, count]) => <option key={status} value={status}>{labels[status] || status} · {count.toLocaleString()}개</option>)}
      </select></label>
      <p role="status">{resultPage.total === 0 ? '해당하는 파일이 없습니다.' : `${(resultPage.page * pageSize + 1).toLocaleString()}–${Math.min((resultPage.page + 1) * pageSize, resultPage.total).toLocaleString()} / ${resultPage.total.toLocaleString()}개`}</p>
      {resultPage.total > 0 && <>
        <details><summary>파일 목록 보기</summary><ul>{resultPage.files.map(item => <li key={item.path}>{item.path} · {labels[item.status] || item.status}</li>)}</ul></details>
        <button type="button" disabled={resultPage.page === 0} onClick={() => setPage(resultPage.page - 1)}>이전 파일</button>
        <button type="button" disabled={(resultPage.page + 1) * pageSize >= resultPage.total} onClick={() => setPage(resultPage.page + 1)}>다음 파일</button>
      </>}
    </div>}
  </section>;
}
