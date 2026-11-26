import React, {useEffect, useId, useRef, useState} from 'react';
import {managementCommand, untilAborted} from './managementCommand.js';
import {requestErrorMessage} from './requestError.mjs';
import {installationJobs, partialDownloadCandidates, preferredCurrentInstallation, relatedActivity, searchCatalog, sortCatalog, validCatalogOverview, validCatalogHistory, validCatalogVerification, withObservedPartialDownloads} from './modelCatalogSearch.mjs';
import {backupTargetLabel, verificationSummary} from './modelBackupResults.mjs';

const kindLabels = {model: '모델', shared: '공유 구성요소', cache: '캐시', collection: '구성요소 모음'};
const present = value => value === true ? '있음' : value === false ? '없음' : '확인 불가';
const manifestLabel = value => ({missing: '없음', read: '읽음', unavailable: '확인 불가', ready_record: '준비 기록', prepared_record: '준비 기록'}[value] || '확인되지 않음');
const fileCount = value => value == null ? '확인 불가' : `${value}개`;
const gib = bytes => `${(bytes / 1024 ** 3).toFixed(2)} GiB`;
const fileSize = bytes => bytes < 1024 ** 3 ? `${(bytes / 1024 ** 2).toFixed(2)} MiB` : gib(bytes);
const restoreLabel = record => record ? `스냅샷 ${record.snapshot_id} · ${record.observed_at} · ${record.files}개 파일 · 백업 당시 해시로 복원 · 수정 시각 불일치 ${record.timestamp_mismatches}개 · 미완료 확장자 ${record.partial_files}개 · 최신 스냅샷 ID ${record.latest_snapshot_match === true ? '일치' : record.latest_snapshot_match === false ? '다름' : '확인 불가'}` : '기록 확인 불가';

export default function ModelCatalog({onCompare}) {
  const busyId=useId();
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState('');
  const searchRef = useRef(null);
  const requestRef = useRef(null);
  const [order, setOrder] = useState('catalog');
  const [partialOnly, setPartialOnly] = useState(false);
  const [checkedAt, setCheckedAt] = useState(null);
  const [jobs, setJobs] = useState(null);
  const [jobsError, setJobsError] = useState('');
  const [verificationRecords, setVerificationRecords] = useState({});
  useEffect(() => () => {const request=requestRef.current; requestRef.current=null; request?.abort();}, []);
  async function load() {
    if (requestRef.current) return;
    const controller=new AbortController(); requestRef.current=controller; let timedOut=false;
    const timeout=setTimeout(() => {timedOut=true; controller.abort();}, 30000);
    setBusy(true); setError('');
    try {
      const [next, history] = await untilAborted(Promise.allSettled([
        managementCommand('model-downloads', 'catalog-overview', {}, {signal:controller.signal}),
        managementCommand('model-downloads', 'backup-verify-history', {}, {signal:controller.signal})
      ]),controller.signal);
      if (next.status === 'rejected') throw next.reason;
      const value = next.value;
      if (!validCatalogOverview(value)) throw new Error('카탈로그 응답 형식이 올바르지 않습니다.');
      const validHistory=history.status === 'fulfilled' && validCatalogHistory(history.value);
      const recent = validHistory ? history.value.records : [];
      const targets = value.components.flatMap(component => {
        const entries = component.alternate_installations || [];
        if (!entries.some(entry => entry.retained_original)) return [];
        const path = component.declaration.path;
        const active = component.presence?.local_present === true && !path.includes('/')
          ? {backup_target: path} : preferredCurrentInstallation(entries);
        return active ? [active.backup_target] : [];
      });
      const checks = await untilAborted(Promise.all(targets.map(async target => {
        const job = recent.find(record => record.model === target && record.operation !== 'sync');
        if (!job) return [target, null];
        try {const record=await managementCommand('model-downloads', 'backup-verify-status', {job_id: job.job_id}, {signal:controller.signal});return [target, validCatalogVerification(record,job.job_id,target) ? record : {status:'unavailable'}];}
        catch {return [target, {status: 'unavailable'}];}
      })),controller.signal);
      if (requestRef.current!==controller || controller.signal.aborted) return;
      if (validHistory) {
        setJobs(history.value.records); setJobsError('');
      } else {
        setJobs(null); setJobsError('최근 백업·검증 작업을 조회하지 못했습니다.');
      }
      setVerificationRecords(Object.fromEntries(checks));
      setResult(value);
      setCheckedAt(new Date());
    } catch (problem) {if(requestRef.current===controller)setError(timedOut ? '카탈로그 조회 시간이 초과됐습니다. 다시 조회하세요.' : '카탈로그를 조회하지 못했습니다. '+requestErrorMessage(problem));}
    finally {clearTimeout(timeout); if(requestRef.current===controller){requestRef.current=null; setBusy(false);}}
  }
  const visibleComponents=result ? sortCatalog(partialOnly ? withObservedPartialDownloads(searchCatalog(result.components,query)) : searchCatalog(result.components,query),order) : [];
  return <section className="model-catalog"><h2>모델 카탈로그</h2>
    <p>등록된 모델과 공유 구성요소, 아직 분류하지 않은 디렉터리를 확인합니다. 표시된 관계는 현재 등록된 정보이며 전체 의존성을 보장하지 않습니다.</p>
    <button type="button" onClick={load} aria-disabled={busy} aria-describedby={busy ? busyId : undefined}>{busy ? '카탈로그 조회 중…' : '카탈로그 조회'}</button>
    {busy && <p id={busyId} role="status">카탈로그를 조회하고 있습니다.{result && ' 아래는 마지막 조회 결과입니다.'}</p>}
    {error && <p role="alert">{error}{result && ' · 이전 조회 결과를 표시합니다.'}</p>}
    {result && <>
      {result.backup_error && <p role="status">{result.backup_error} 백업 존재 여부는 확인할 수 없습니다.</p>}
      {jobsError && <p role="status">{jobsError}</p>}
      {result.activity && <details><summary>GPU 대기열과 예약 관측</summary>
        <p>조회 시점의 공용 대기열과 예약 기록입니다. 직접 실행한 작업이나 모델 파일 사용 여부는 확인할 수 없으며, 항목이 없어도 정리 가능을 뜻하지 않습니다.</p>
        <p>대기열 · {result.activity.queue?.status === 'available' ? `${result.activity.queue.jobs.length}건` : '확인 불가'} · 예약 기록 · {result.activity.reservations?.status === 'available' ? `${result.activity.reservations.records.length}건${result.activity.reservations.truncated ? ' 이상' : ''}` : '확인 불가'}</p>
        <ul>{(result.activity.queue?.jobs || []).map(job => <li key={`queue-${job.service}-${job.id}`}>대기 · {job.source_service || job.service} · {job.id} · 실행기 {job.executor_identity === 'verified' ? '확인됨' : '확인 불가'}</li>)}
          {(result.activity.reservations?.records || []).map((job, index) => <li key={`reservation-${index}`}>예약 기록 · {job.source_service || job.service || '서비스 확인 불가'} · {job.job_id || '작업 확인 불가'} · {job.state === 'recorded' ? '기록됨' : '상태 확인 필요'}</li>)}</ul>
      </details>}
      {jobs && <details><summary>최근 백업·검증 작업 {jobs.length}건</summary><p>최근 20건 기준이며 완료는 해시 일치를 뜻하지 않습니다. 복원 시험과 생성기 작업 상태는 여기에 포함되지 않습니다.</p><ul>{jobs.map(job => <li key={job.job_id}>{job.model || '대상 확인 불가'} · {job.operation === 'sync' ? '백업' : '검증'} · {({running: '진행 중', completed: '완료', failed: '실패', interrupted: '중단됨'}[job.status] || '상태 확인 불가')} · {job.started_at || '시각 확인 불가'} {job.model && <button type="button" aria-label={`${job.model} · ${job.job_id} 이 작업의 상태·결과 보기`} onClick={() => onCompare?.(job.model, job.job_id)}>이 작업의 상태·결과 보기</button>}</li>)}</ul></details>}
      <details><summary>미완료 다운로드 관측 · {result.storage_survey ? `${partialDownloadCandidates(result.components).length}개 경로` : '조사 기록 확인 불가'}</summary>
        <p>이전 조사에서 확장자로 식별한 파일입니다. 대기열과 예약은 등록 서비스 기준이며 직접 실행한 작업이나 실제 파일 사용 여부는 포함하지 않습니다. 현재 다운로드 진행 여부, 재사용 필요성과 실제 회수 가능 용량은 확인되지 않았습니다. 공유 의존성과 백업·복원 상태를 확인하기 전에는 삭제하지 마세요.</p>
        {!result.storage_survey ? <p>조사 기록을 사용할 수 없습니다.</p> : <ul>{partialDownloadCandidates(result.components).map(candidate => {
          const activity = relatedActivity(result.activity, candidate.declaration.services);
          const matchingJobs = installationJobs(jobs, candidate.backup_target);
          return <li key={`${candidate.declaration.id}:${candidate.path}`}><strong>{candidate.declaration.label}</strong> · {candidate.path} · 미완료 확장자 {candidate.storage_observation.partial_files}개 · 당시 할당 크기 {gib(candidate.storage_observation.partial_allocated_bytes)} · 등록 서비스 {candidate.declaration.services.join(', ') || '확인되지 않음'}<br/>
            관련 서비스 대기 {candidate.declaration.services.length && result.activity?.queue?.status === 'available' ? `${activity.queued.length}건` : '확인 불가'} · 예약 {candidate.declaration.services.length && result.activity?.reservations?.status === 'available' && !result.activity.reservations.truncated ? `${activity.reservations.length}건` : '확인 불가'} · 최근 20건 중 백업·검증 작업 {jobs && candidate.backup_target ? `${matchingJobs.length}건 (진행 중 ${matchingJobs.filter(job => job.status === 'running').length}건)` : '확인 불가'}<br/>
            백업 대상 {candidate.backup_target || '확인 불가'} · 완료 스냅샷 {present(candidate.snapshot_present)} · 과거 복원 기록 {restoreLabel(candidate.restore_record)} {candidate.backup_target && <button type="button" aria-label={`${candidate.path} 미완료 파일의 백업 비교로 이동`} onClick={() => onCompare?.(candidate.backup_target)}>백업 비교로 이동</button>}</li>;
        })}</ul>}
      </details>
      <details><summary>이관 후 보존 원본 확인</summary>
        <p>되돌리기용 원본입니다. 관측 크기는 회수 가능 용량이나 삭제 가능 판정이 아닙니다. 백업·검증 작업 수는 전체 대상의 최근 20건 중 해당 설치 경로의 기록이며, 상위 폴더나 이전 경로의 기록은 포함하지 않습니다. 복원 기록은 해당 대상의 과거 관측이며 현재 스냅샷의 상태를 보장하지 않습니다. 실제 파일 사용 여부는 확인되지 않았습니다.</p>
        <ul>{result.components.flatMap(({declaration: item, presence, restore_record: restoreRecord, alternate_installations: alternates = []}) => {
          const current = presence?.local_present === true && !item.path.includes('/')
            ? {...presence, path: item.path, backup_target: item.path, restore_record: restoreRecord}
            : preferredCurrentInstallation(alternates);
          const activity = relatedActivity(result.activity, item.services);
          const matchingJobs = installationJobs(jobs, current?.backup_target);
          const verification = current && verificationRecords[current.backup_target];
          return alternates.filter(alt => alt.retained_original).map(alt => <li key={alt.path}>
            <strong>{item.label}</strong> · 보존 원본 {alt.path} · 관측 할당 크기 {alt.storage_observation ? gib(alt.storage_observation.allocated_bytes) : '확인 불가'} · 관측 시각 {alt.storage_observation?.observed_at || '확인 불가'}{alt.storage_observation?.errors || alt.storage_observation?.changed ? ' · 조사 오류 또는 변경 감지' : ''}<br/>
            이관 기록 · {alt.copy_record?.kind === 'recorded_source_copy_sha256' ? `원본과 복사본 SHA-256 대조 ${alt.copy_record.file_count}개 파일 기록됨 · 현재 일치 여부 별도 확인` : alt.copy_record?.kind === 'recorded_fixed_sha256' ? `고정 SHA-256 ${alt.copy_record.sha256} 기록됨 · 현재 일치 여부 별도 확인` : '복사본 대조 기록 확인 불가'}<br/>
            현재 설치본 {current?.path || '확인 불가'} · 백업 대상 {current?.backup_target || '확인 불가'} · 현재 경로의 기존 백업 {present(current?.backup_present)} · 완료 스냅샷 {present(current?.snapshot_present)} · 서비스 {item.services.join(', ') || '확인되지 않음'}
            {current && <button type="button" aria-label={`${item.label} · ${current.path} 현재 설치본 백업 확인`} onClick={() => onCompare?.(current.backup_target)}>현재 설치본 백업 확인</button>}
            <br/>관련 서비스 관측 · 대기 {item.services.length && result.activity?.queue?.status === 'available' ? `${activity.queued.length}건` : '확인 불가'} · 예약 {item.services.length && result.activity?.reservations?.status === 'available' && !result.activity.reservations.truncated ? `${activity.reservations.length}건` : '확인 불가'} · 최근 백업·검증 작업 {jobs && current ? `${matchingJobs.length}건` : '확인 불가'} · 회수 가능 용량 확인 불가
            {matchingJobs.length > 0 && <button type="button" aria-label={`${item.label} · ${current.path} 최근 작업 결과 보기`} onClick={() => onCompare?.(current.backup_target, matchingJobs[0].job_id)}>최근 작업 결과 보기</button>}
            <br/>최근 검증 기록 · {verification ? <>{verification.status === 'completed' ? verificationSummary(verification.result) || '상세 결과 확인 필요' : ({running:'진행 중', failed:'실패', interrupted:'중단됨'}[verification.status] || '확인 불가')} · 대상 {backupTargetLabel(verification.target)} · 시각 {verification.finished_at || verification.started_at || '확인 불가'} · 과거 결과이며 현재 상태는 별도 확인</> : jobs ? '최근 20건에 없음' : '확인 불가'}
            <br/>이 백업 대상의 과거 복원 기록 · {restoreLabel(current?.restore_record)} · 현재 내용 무결성과 추론 성공은 별도 확인
          </li>);
        })}</ul>
      </details>
      <p>마지막 조회 · {checkedAt?.toLocaleString('ko-KR')}</p>
      {result.storage_survey && <p>저장 공간 조사 · {result.storage_survey.finished_at || '시각 확인 불가'} · 과거 관측값이며 현재 용량과 다를 수 있습니다. 링크 대상은 포함하지 않으며 하드링크가 중복 계산될 수 있습니다. 기존 경로가 없으면 추가 설치본의 크기로 정렬합니다.{(result.storage_survey.changed || result.storage_survey.errors) && ' 조사 중 변경 또는 오류가 감지되었습니다.'}</p>}
      {!result.storage_survey && <p>저장 공간 조사 기록을 사용할 수 없어 모델별 내부 조사 결과를 확인할 수 없습니다.</p>}
      <label>카탈로그 검색 <input ref={searchRef} type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="모델, 서비스, 출처, 경로"/></label>
      <label>정렬 <select value={order} onChange={event => setOrder(event.target.value)}><option value="catalog">카탈로그 순서</option><option value="allocated">이전 조사 할당 크기순</option></select></label>
      <label><input type="checkbox" checked={partialOnly} onChange={event => setPartialOnly(event.target.checked)}/> 미완료 확장자 관측 항목만 보기</label>
      {partialOnly && <p>마지막 조사에서 확장자로 관측된 항목만 표시합니다. 조사 기록이 없는 항목은 확인 불가이며, 삭제 가능하다는 뜻이 아닙니다.</p>}
      {query && <button type="button" onClick={() => {setQuery(''); searchRef.current?.focus();}}>카탈로그 검색 지우기</button>}
      <p role="status">검색 결과 {visibleComponents.length}개 / 등록 {result.components.length}개 · 미분류 디렉터리 {result.unclassified.length}개</p>
      {visibleComponents.length===0 && <p>{result.components.length===0 ? '등록된 카탈로그 항목이 없습니다.' : '일치하는 등록 항목이 없습니다. 검색어나 필터를 확인하세요.'}</p>}
      {visibleComponents.length>0 && <ul>{visibleComponents.map(({declaration: item, declared_version: version, presence: state, installation_metadata: installed, restore_record: restoreRecord, storage_observation: storage, observed_links: links, alternate_installations: alternates}) => {
        const current = preferredCurrentInstallation(alternates);
        const legacy = current && state?.local_present !== true;
        const currentTarget = legacy ? current.backup_target : (!item.path.includes('/') ? item.path : null);
        const matchingJobs = installationJobs(jobs, currentTarget);
        const activity = relatedActivity(result.activity, item.services);
        return <li key={item.id}>
        <strong>{item.label}</strong> · {kindLabels[item.kind] || item.kind} · {item.id}<br/>
        {legacy ? <>현재 설치 경로 · {current.path} · 서비스 · {item.services.map(service => service + (item.optional_services?.includes(service) ? ' (선택)' : '')).join(', ') || '확인되지 않음'}<br/>
          백업 대상 {current.backup_target} · 로컬 {present(current.local_present)} · 현재 경로의 기존 백업 {present(current.backup_present)} · 완료 스냅샷 {present(current.snapshot_present)}
          <button type="button" aria-label={`${item.label} · ${current.path} 현재 설치본의 백업 비교로 이동`} onClick={() => onCompare?.(current.backup_target)}>현재 설치본의 백업 비교로 이동</button><br/>
          이관 전 경로 · {item.path} · 로컬 {present(state?.local_present)} · 이전 경로의 기존 백업 {present(current.legacy_backup_present ?? state?.backup_present)} · 이전 경로 스냅샷 {present(state?.snapshot_present)}<br/></>
          : <>경로 · {item.path} · 서비스 · {item.services.map(service => service + (item.optional_services?.includes(service) ? ' (선택)' : '')).join(', ') || '확인되지 않음'}<br/></>}
        출처 · {item.source || '확인되지 않음'} · 선언 리비전 · {item.revision || '확인되지 않음'}<br/>
        선언 버전 · {version?.id || '확인되지 않음'}{version && ' · 설치본과의 일치 여부는 별도 확인'}<br/>
        {item.usage_note && <>안내 · {item.usage_note}<br/></>}
        {result.activity && (activity.queued.length > 0 || activity.reservations.length > 0) && <p>등록된 관련 서비스의 관측 기록 · 대기 {activity.queued.length}건 · 예약 {activity.reservations.length}건 · 해당 모델의 실제 사용 여부는 별도 확인</p>}
        설치 매니페스트 · {manifestLabel((legacy ? current.installation_metadata : installed)?.manifest_state)} · 선언 파일 {fileCount((legacy ? current.installation_metadata : installed)?.declared_file_count)}
        {(legacy ? current.installation_metadata : installed)?.declared_sources?.length > 0 && <> · 설치 기록 출처 {(legacy ? current.installation_metadata : installed).declared_sources.map(source => `${source.repository}@${source.revision}`).join(', ')}</>}<br/>
        {!legacy && <>{state && !item.path.includes('/') && <>백업 대상 {item.path} · </>}로컬 {present(state?.local_present)} · 기존 백업 {present(state?.backup_present)} · 완료 스냅샷 {present(state?.snapshot_present)}</>}
        {!legacy && state && !item.path.includes('/') && <button type="button" aria-label={`${item.label} · ${item.path} 이 경로의 백업 비교로 이동`} onClick={() => onCompare?.(item.path)}>이 경로의 백업 비교로 이동</button>}
        <p>이 백업 대상의 과거 복원 기록 · {restoreLabel(legacy ? current?.restore_record : restoreRecord)} · 현재 내용 무결성과 추론 성공은 별도</p>
        {currentTarget && jobs && <p>이 설치 경로의 최근 작업 · {matchingJobs.length ? <>{matchingJobs.length}건 <button type="button" aria-label={`${item.label} · ${currentTarget} 가장 최근 작업 결과 보기`} onClick={() => onCompare?.(currentTarget, matchingJobs[0].job_id)}>가장 최근 작업 결과 보기</button></> : '최근 20건에 없음'} · 다른 경로나 상위 폴더의 작업은 포함하지 않음</p>}
        {storage && <p>이전 조사 · 논리 크기 {gib(storage.logical_bytes)} · 할당 크기 {gib(storage.allocated_bytes)} · 파일 {storage.files}개 · 링크 {storage.links}개 · 오류 {storage.errors}개{storage.partial_files > 0 && <> · 미완료 확장자 파일 {storage.partial_files}개 · 관측 할당 크기 {gib(storage.partial_allocated_bytes)} · 삭제 가능 여부 별도 확인</>}</p>}
        {links?.length > 0 && <details><summary aria-label={`${item.label} · ${item.path} 조사에서 발견한 관련 링크 ${links.length}개`}>조사에서 발견한 관련 링크 {links.length}개</summary><p>링크와 대상 경로는 조사 당시의 관측값입니다. 폴더를 이동하면 참조가 끊어질 수 있습니다.</p><ul>{links.map(link => <li key={link.path}>{link.path} → {link.resolved} · {({present: '대상 있음', missing: '대상 없음', outside: '모델 루트 밖', unknown: '상태 확인 불가'}[link.status] || '상태 확인 불가')}</li>)}</ul></details>}
        {legacy && current.storage_observation && <p>현재 설치본의 이전 조사 · 할당 크기 {gib(current.storage_observation.allocated_bytes)}</p>}
        {alternates?.filter(alt => !legacy || alt !== current).map(alt => <p key={`${alt.path}:${alt.backup_target || ''}`}>{alt.retained_original ? '별도 보존 원본' : alt.external_cache ? '별도 캐시' : alt.path === item.path || alt.path === current?.path ? '동일 경로의 백업 대상' : '추가 설치본'} · {alt.path} · {alt.retained_original ? <>모델 백업 대상 경로 밖에 보존됨 · 정리 보류{alt.storage_observation && ` · 관측 할당 크기 ${gib(alt.storage_observation.allocated_bytes)} · ${alt.storage_observation.observed_at}${alt.storage_observation.errors || alt.storage_observation.changed ? ' · 조사 오류 또는 변경 감지' : ''}`} · 새 백업과 복원 검증 전에는 보존</> : alt.external_cache ? '모델 백업 대상 경로 밖에 있음' : <>백업 대상 {alt.backup_target} · 로컬 {present(alt.local_present)} · 기존 백업 {present(alt.backup_present)} · 완료 스냅샷 {present(alt.snapshot_present)}{alt.storage_observation && ` · 이전 조사 할당 크기 ${gib(alt.storage_observation.allocated_bytes)}`}{alt.installation_metadata && ` · 설치 매니페스트 ${manifestLabel(alt.installation_metadata.manifest_state)} · 선언 파일 ${fileCount(alt.installation_metadata.declared_file_count)}`} <button type="button" aria-label={`${item.label} · ${alt.path} · 백업 대상 ${alt.backup_target} 이 설치본의 백업 비교로 이동`} onClick={() => onCompare?.(alt.backup_target)}>이 설치본의 백업 비교로 이동</button></>}</p>)}
      </li>})}</ul>}
      <details><summary>미분류 디렉터리 {result.unclassified.length}개 보기</summary>
        <p>미분류는 미사용이나 삭제 가능을 뜻하지 않습니다.</p>
        <ul>{result.unclassified.map(item => <li key={item.name}>{item.name} · {item.partially_classified && '일부 구성요소 등록됨 · '}로컬 {present(item.local_present)} · 기존 백업 {present(item.backup_present)} · 완료 스냅샷 {present(item.snapshot_present)} <button type="button" aria-label={`${item.name} 미분류 대상의 백업 비교로 이동`} onClick={() => onCompare?.(item.name)}>백업 비교로 이동</button></li>)}</ul>
        {result.storage_survey && <><p>아래 `models/` 하위 항목은 {result.storage_survey.finished_at || '시각 확인 불가'} 조사 기준이며 현재 파일 존재나 사용 여부를 확정하지 않습니다.</p>
          {!result.nested_survey_available ? <p>이전 `models/` 경로의 하위 조사 정보가 없어 해당 경로의 분류 여부를 확인할 수 없습니다.</p> : result.unclassified_nested?.length ? <ul>{result.unclassified_nested.map(item => <li key={item.path}>{item.path} · 조사 당시 할당 크기 {gib(item.storage_observation.allocated_bytes)} · 파일 {item.storage_observation.files}개</li>)}</ul> : <p>조사된 `models/` 하위 경로 중 별도 미분류 항목이 없습니다.</p>}</>}
      </details>
      {result.surveyed_model_roots?.length > 0 && <details><summary>모델 디렉터리 내부 조사 · {result.surveyed_model_roots.length}개 모델</summary>
        <p>조사 당시 직계 항목입니다. 이 목록만으로 모델의 사용 여부나 삭제 가능 여부를 판단할 수 없습니다. 링크는 대상을 따라 용량을 더하지 않습니다.</p>
        {result.surveyed_model_roots.map(root => {
          const children = (result.surveyed_model_children || []).filter(item => item.path.startsWith(`${root}/`));
          return <details key={root}><summary>{root} · 직계 항목 {children.length}개</summary>
            {children.length ? <ul>{children.map(item => <li key={item.path}>{item.path} · 조사 당시 할당 크기 {gib(item.storage_observation.allocated_bytes)} · 파일 {item.storage_observation.files}개 · 링크 {item.storage_observation.links}개 · 오류 {item.storage_observation.errors}개{item.storage_observation.changed && ' · 조사 중 변경 감지'}{item.storage_observation.partial_files > 0 && ` · 미완료 확장자 ${item.storage_observation.partial_files}개 · 할당 크기 ${gib(item.storage_observation.partial_allocated_bytes)}`}</li>)}</ul> : <p>표시할 직계 항목 기록이 없습니다. 조사 누락이나 오류 여부를 확인하세요.</p>}
          </details>;
        })}
      </details>}
      {result.duplicate_survey && <details><summary>동일 내용 조사 · {result.duplicate_survey.groups.length}개 그룹</summary>
        <p>조사 시각 {result.duplicate_survey.observed_at} · 조사 오류 {result.duplicate_survey.error_count}건. 스냅샷 기록을 후보로 당시 로컬 파일을 읽은 결과입니다. 서비스와 백업 상태는 카탈로그 조회 시점이며 작업 이력은 최근 20건에 한정됩니다. 대기·예약 관측은 직접 실행한 작업이나 실제 파일 사용 여부를 포함하지 않습니다. 동일 해시 파일을 하나 남겼다고 가정한 논리 크기는 실제 회수 용량이나 삭제 가능성, 공유 호환성을 뜻하지 않습니다.</p>
        {result.duplicate_survey.groups.map((group, index) => <details key={index}><summary>{group.paths[0]?.path.split('/').pop() || '파일'} · 파일당 {fileSize(group.size)} · {group.paths.length}개 경로</summary><p>조사 당시 서로 다른 파일 {group.distinct_files == null ? '확인 불가' : `${group.distinct_files}개`} · 하나만 남긴다고 가정한 나머지 논리 크기 {group.duplicate_logical_bytes == null ? '확인 불가' : fileSize(group.duplicate_logical_bytes)} · 실제 회수 용량 확인 불가</p><ul>{group.paths.map(path => {
          const target = path.path.split('/')[0];
          const matchingJobs = installationJobs(jobs, target);
          const related = relatedActivity(result.activity, path.services || []);
          return <li key={path.path}>{path.path} · {({matches:'조사 당시 해시 일치',different:'조사 당시 해시 다름',unavailable:'확인 불가'}[path.state])}{path.via_link === true && ' · 링크 경유'} · 등록 서비스 {path.services?.join(', ') || '확인되지 않음'} · 해당 모델 일반 대상의 완료 스냅샷 {present(path.snapshot_present)} · 최근 20건 중 이 대상 작업 {jobs ? `${matchingJobs.length}건` : '확인 불가'} · 등록 서비스 관련 대기 {path.services?.length && result.activity?.queue?.status === 'available' ? `${related.queued.length}건` : '확인 불가'} · 예약 {path.services?.length && result.activity?.reservations?.status === 'available' && !result.activity.reservations.truncated ? `${related.reservations.length}건` : '확인 불가'} · 과거 복원 기록 {restoreLabel(path.restore_record)} {matchingJobs.length > 0 && <button type="button" aria-label={`${path.path} · ${target} 최근 백업 작업 보기`} onClick={() => onCompare?.(target, matchingJobs[0].job_id)}>최근 작업 보기</button>}</li>;
        })}</ul></details>)}
      </details>}
      {!result.duplicate_survey && <p>동일 내용 조사 기록을 사용할 수 없습니다. 기록이 없거나 읽을 수 없는 경우이며 중복이 없다는 뜻은 아닙니다.</p>}
      <p>{result.note}</p>
    </>}
  </section>;
}
