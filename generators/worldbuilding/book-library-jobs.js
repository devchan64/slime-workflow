// 도서 편집 전체 실행과 단계별 기록 조회.
const BOOK_STAGE_STATUS_LABELS = {pending:'실행 전',queued:'대기',running:'실행 중',context:'원본 수집 중',generating:'실행 중',completed:'완료',failed:'실패',skipped:'실행 안 함'};
const BOOK_RECORD_TYPE_LABELS = {'request.yaml':'요청','stage-input.yaml':'입력 연결','status.yaml':'상태','execution.log':'실행 로그','book-result.yaml':'단계 결과'};
const BOOK_JOB_POLL_INTERVAL = 3000;
let selectedAutomationTaskId = '';
let automationHistoryOffset = 0;
let automationHistoryTotal = 0;
let automationHistoryPageSize = 20;
let currentActiveTaskIds = [];
let automationRefreshActive = false;
let selectedRecordRelativePath = '';
let currentJobCollectionId = '';
let currentStageRenderSignature = '';
let currentHistoryRenderSignature = '';

function summarizeJobMessage(currentMessageText) {
    const currentFirstLine = (currentMessageText || '').split('\n')[0];
    return currentFirstLine.length > 220 ? currentFirstLine.slice(0,220)+'… (상세 기록에서 확인)' : currentFirstLine;
}

function updateAutomationControls() {
    document.querySelector('#automateBook').disabled = currentRequestActive || currentActiveTaskIds.length > 0 || !currentLibraryState || !findSelectedCollection().source_directory_paths.length;
    document.querySelector('#automateBook').textContent = currentActiveTaskIds.length ? '도서 편집 실행 중' : '1~4단계 한 번에 실행';
    document.querySelector('#historyPreviousPage').disabled = currentRequestActive || automationHistoryOffset === 0;
    document.querySelector('#historyNextPage').disabled = currentRequestActive || automationHistoryOffset + automationHistoryPageSize >= automationHistoryTotal;
}

async function showAutomationRecord(currentTaskIdentifier, currentRelativePath) {
    const currentRecordValues = await requestBookApi('book-job-record', {workflow_task_id:currentTaskIdentifier, relative_path:currentRelativePath});
    if (selectedAutomationTaskId !== currentTaskIdentifier) return;
    selectedRecordRelativePath = currentRelativePath;
    document.querySelector('#recordPathText').textContent = currentRecordValues.absolute_path;
    document.querySelector('#recordContentText').textContent = currentRecordValues.content_text;
    document.querySelector('#recordLimitText').textContent = currentRecordValues.truncated_flag ? (currentRecordValues.tail_flag ? '큰 로그의 마지막 부분을 표시합니다. 전체 파일은 표시된 경로에 있습니다.' : '큰 파일의 앞부분을 표시합니다. 전체 파일은 표시된 경로에 있습니다.') : '';
    document.querySelector('#recordOpenLink').href = currentRecordValues.read_url;
    document.querySelector('#recordViewerPanel').hidden = false;
    document.querySelector('#artifactSelectPath').value = currentRelativePath;
}

async function showAutomationDetails(currentTaskIdentifier) {
    const currentDetailValues = await requestBookApi('book-job-detail', {workflow_task_id:currentTaskIdentifier});
    if (currentDetailValues.collection_id !== selectedCollectionId || selectedAutomationTaskId !== currentTaskIdentifier) return;
    document.querySelector('#jobDetailPanel').hidden = false;
    document.querySelector('#jobDetailSummary').textContent = currentTaskIdentifier + ' · ' + (BOOK_STAGE_STATUS_LABELS[currentDetailValues.current_stage_name] || currentDetailValues.current_stage_name);
    document.querySelector('#jobDirectoryPath').textContent = currentDetailValues.run_directory;
    document.querySelector('#jobDetailFailure').textContent = currentDetailValues.failure_reason_text || '';
    const currentStageList = document.querySelector('#jobStageList');
    const currentStageSignature = JSON.stringify(currentDetailValues.stage_entries);
    if (currentStageRenderSignature !== currentStageSignature) {
    currentStageRenderSignature = currentStageSignature;
    currentStageList.replaceChildren();
    for (const currentStageEntry of currentDetailValues.stage_entries) {
        const currentStageCard = createBookElement('div','');
        currentStageCard.className = 'stage-card';
        currentStageCard.append(createBookElement('h3',(currentStageEntry.stage_number ? currentStageEntry.stage_number+'. ' : '')+currentStageEntry.stage_label+' · '+(BOOK_STAGE_STATUS_LABELS[currentStageEntry.current_stage_name] || currentStageEntry.current_stage_name)));
        currentStageCard.append(createBookElement('p',summarizeJobMessage(currentStageEntry.failure_reason_text || currentStageEntry.result_summary_text)));
        currentStageCard.append(createBookElement('p','시작: '+(currentStageEntry.started_timestamp_text || '—')+' · 종료: '+(currentStageEntry.finished_timestamp_text || '—')));
        const currentStagePath = createBookElement('p',currentStageEntry.run_directory);
        currentStagePath.className = 'record-path';
        currentStageCard.append(currentStagePath);
        const currentStageActions = createBookElement('div','');
        currentStageActions.className = 'actions';
        for (const currentArtifactEntry of currentStageEntry.artifacts) {
            const currentRecordButton = createBookElement('button',(BOOK_RECORD_TYPE_LABELS[currentArtifactEntry.relative_path.split('/').pop()] || '기록')+' 조회');
            currentRecordButton.onclick = () => executeBookAction(() => showAutomationRecord(currentTaskIdentifier,currentArtifactEntry.relative_path));
            currentStageActions.append(currentRecordButton);
        }
        currentStageCard.append(currentStageActions);
        currentStageList.append(currentStageCard);
    }
    }
    const currentArtifactSelect = document.querySelector('#artifactSelectPath');
    const currentArtifactSelection = currentArtifactSelect.value;
    currentArtifactSelect.replaceChildren();
    for (const currentArtifactEntry of currentDetailValues.artifacts) {
        const currentArtifactOption = createBookElement('option',currentArtifactEntry.relative_path+' · '+currentArtifactEntry.byte_count+' bytes');
        currentArtifactOption.value = currentArtifactEntry.relative_path;
        currentArtifactSelect.append(currentArtifactOption);
    }
    if (currentDetailValues.artifacts.some(currentArtifactEntry => currentArtifactEntry.relative_path === currentArtifactSelection)) currentArtifactSelect.value = currentArtifactSelection;
    else if (currentDetailValues.artifacts.some(currentArtifactEntry => currentArtifactEntry.relative_path === selectedRecordRelativePath)) currentArtifactSelect.value = selectedRecordRelativePath;
    const currentCompletedArtifact = currentDetailValues.artifacts.find(currentArtifactEntry => currentArtifactEntry.relative_path.endsWith('completed-book/README.md'));
    document.querySelector('#viewCompletedBook').hidden = !currentCompletedArtifact;
    document.querySelector('#viewCompletedBook').onclick = () => executeBookAction(() => showAutomationRecord(currentTaskIdentifier,currentCompletedArtifact.relative_path));
}

async function refreshAutomationJobs() {
    if (automationRefreshActive) return;
    automationRefreshActive = true;
    const currentCollectionRequest = selectedCollectionId;
    try {
        if (currentJobCollectionId !== selectedCollectionId) {
            currentJobCollectionId = selectedCollectionId;
            automationHistoryOffset = 0;
            currentStageRenderSignature = '';
            currentHistoryRenderSignature = '';
            selectedAutomationTaskId = '';
            selectedRecordRelativePath = '';
            currentActiveTaskIds = [];
            document.querySelector('#jobDetailPanel').hidden = true;
            document.querySelector('#recordViewerPanel').hidden = true;
        }
        const currentStateResponse = await fetch('/worldbuilding/api/state');
        if (!currentStateResponse.ok) throw new Error('작업 상태 조회 실패');
        const currentStateValues = await currentStateResponse.json();
        managementCsrfToken = currentStateValues.management_csrf_token;
        const currentJobsResponse = await fetch('/worldbuilding/api/book-jobs?collection_id='+encodeURIComponent(currentCollectionRequest)+'&offset='+automationHistoryOffset);
        const currentJobsValues = await currentJobsResponse.json();
        if (!currentJobsResponse.ok) throw new Error(currentJobsValues.failure_reason_text || '도서 기록 조회 실패');
        if (currentCollectionRequest !== selectedCollectionId) return;
        currentActiveTaskIds = currentJobsValues.active_task_identifiers;
        automationHistoryTotal = currentJobsValues.total_count;
        automationHistoryPageSize = currentJobsValues.page_size;
        document.querySelector('#automationEnvironmentText').textContent = currentStateValues.worker_failure_text || (!currentStateValues.runtime_prepared_flag ? '모델 환경 준비가 필요합니다. 세계관 작성·정리 화면에서 실행 환경을 준비하세요.' : '실행 기록은 저장되며 새로고침하거나 화면을 닫아도 작업이 이어집니다.');
        document.querySelector('#historyPageText').textContent = '전체 '+automationHistoryTotal+'건 · '+(automationHistoryTotal ? automationHistoryOffset+1 : 0)+'~'+Math.min(automationHistoryOffset+automationHistoryPageSize,automationHistoryTotal);
        const currentJobsList = document.querySelector('#automationJobs');
        const currentHistorySignature = JSON.stringify(currentJobsValues.job_entries);
        if (currentHistoryRenderSignature !== currentHistorySignature) {
        currentHistoryRenderSignature = currentHistorySignature;
        currentJobsList.replaceChildren();
        for (const currentJobEntry of currentJobsValues.job_entries) {
            const currentJobCard = createBookElement('div','');
            currentJobCard.className = 'book-card';
            currentJobCard.append(createBookElement('h3',(currentJobEntry.book_edit_stage_name==='all-stages' ? '1~4단계 전체 실행' : '개별 단계 실행')+' · '+(BOOK_STAGE_STATUS_LABELS[currentJobEntry.current_stage_name] || currentJobEntry.current_stage_name)));
            currentJobCard.append(createBookElement('p',currentJobEntry.workflow_task_id+' · '+summarizeJobMessage(currentJobEntry.failure_reason_text || currentJobEntry.result_summary_text || currentJobEntry.requested_instruction_text)));
            currentJobCard.append(createBookElement('p',currentJobEntry.stage_entries.map(currentStageEntry => currentStageEntry.stage_label+': '+(BOOK_STAGE_STATUS_LABELS[currentStageEntry.current_stage_name] || currentStageEntry.current_stage_name)).join(' → ')));
            const currentJobPath = createBookElement('p',currentJobEntry.run_directory);
            currentJobPath.className = 'record-path';
            currentJobCard.append(currentJobPath);
            const currentDetailsButton = createBookElement('button','단계별 기록·경로 조회');
            currentDetailsButton.onclick = () => executeBookAction(async () => {
                selectedAutomationTaskId = currentJobEntry.workflow_task_id;
                selectedRecordRelativePath = '';
                document.querySelector('#recordViewerPanel').hidden = true;
                await showAutomationDetails(selectedAutomationTaskId);
            });
            currentJobCard.append(currentDetailsButton);
            currentJobsList.append(currentJobCard);
        }
        if (!currentJobsList.children.length) currentJobsList.textContent = '실행 기록이 없습니다. 위 버튼으로 1~4단계를 시작하세요.';
        }
        if (selectedAutomationTaskId) await showAutomationDetails(selectedAutomationTaskId);
    } finally {
        automationRefreshActive = false;
        updateAutomationControls();
    }
}

document.querySelector('#automateBook').onclick = () => executeBookAction(async () => {
    const currentCollectionEntry = findSelectedCollection();
    const currentTaskValues = await requestBookApi('book-ai',{collection_id:selectedCollectionId,book_title_text:currentCollectionEntry.book_title_text,source_directory_paths:currentCollectionEntry.source_directory_paths,requested_instruction_text:document.querySelector('#bookEditInstruction').value.trim(),book_edit_stage_name:'all-stages'});
    selectedAutomationTaskId = currentTaskValues.workflow_task_id;
    automationHistoryOffset = 0;
    showBookFeedback((currentTaskValues.already_running_flag ? '이미 실행 중인 작업을 표시합니다: ' : '1~4단계 순차 실행을 등록했습니다: ')+currentTaskValues.workflow_task_id);
    await refreshAutomationJobs();
});
document.querySelector('#historyPreviousPage').onclick = () => executeBookAction(async () => { automationHistoryOffset = Math.max(0,automationHistoryOffset-automationHistoryPageSize); await refreshAutomationJobs(); });
document.querySelector('#historyNextPage').onclick = () => executeBookAction(async () => { automationHistoryOffset += automationHistoryPageSize; await refreshAutomationJobs(); });
document.querySelector('#readSelectedArtifact').onclick = () => executeBookAction(() => showAutomationRecord(selectedAutomationTaskId,document.querySelector('#artifactSelectPath').value));
setInterval(() => { if (!currentRequestActive) refreshAutomationJobs().catch(currentRequestError => showBookFeedback(currentRequestError.message,true)); }, BOOK_JOB_POLL_INTERVAL);
document.querySelector('#paragraphSearch').oninput = renderBookParagraphs;
document.querySelector('#refreshLibrary').onclick = () => executeBookAction(async () => { await refreshBookLibrary(); showBookFeedback('도서와 실행 기록을 새로 불러왔습니다.'); });
executeBookAction(refreshBookLibrary);
