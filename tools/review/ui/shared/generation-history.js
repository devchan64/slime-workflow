// 생성기별 페이지는 빈 컨테이너와 API 경로만 제공한다. 이력 UI는 이 파일에서 공통 관리한다.
const generationHistoryContainer=document.querySelector('#generation-history');
const usesSelectionActions=generationHistoryContainer.dataset.selectionActions==='true';
const allowsIndividualHistoryDelete=generationHistoryContainer.dataset.individualHistoryDelete==='true';
generationHistoryContainer.classList.toggle('uses-selection-actions',usesSelectionActions);
generationHistoryContainer.innerHTML='<div class="history-heading"><div><h2>생성 이력</h2><p>결과는 누적 보관됩니다. 목록 초기화는 수동으로 실행하며 원본 파일은 유지됩니다.</p></div></div><div class="history-filters"><label>이력 검색<input id="history-search" type="search" placeholder="ID·모션·프롬프트 검색"></label><label>작업 상태<select id="history-state-filter"><option value="">전체 상태</option><option value="completed">완료</option><option value="queued">GPU 대기 중</option><option value="running">생성 중</option><option value="failed">실패</option><option value="cancelled">취소됨</option></select></label></div><div class="history-management-actions history-navigation-actions"><p id="history-status" role="status"></p><button type="button" id="history-refresh">이력 새로고침</button><button id="history-prev" type="button">← 이전</button><span id="history-page"></span><button id="history-next" type="button">다음 →</button></div><ul id="history-list"></ul><p id="history-result-reference" hidden aria-live="polite"></p><details id="history-log-details"><summary>선택한 작업 로그</summary><pre id="history-log">이력에서 로그 보기를 선택하세요.</pre></details><details id="history-reset-details"><summary>이력 수동 초기화</summary><p>이력 목록만 초기화하며 결과·입력·로그 파일은 유지합니다.</p><button type="button" id="history-reset" class="danger">이력 목록 초기화</button></details>';
if(generationHistoryContainer.dataset.resetDeletesFiles==='true')generationHistoryContainer.querySelector('.history-heading p').textContent='수동 초기화하면 이력과 참조·결과·로그 파일이 함께 삭제됩니다. 정식 등록 에셋은 유지됩니다.';
let currentHistoryPage=1,selectedHistoryIdentifier=null,historyLogPollTimer=null;
const historyPageSize=8;
async function loadSelectedHistoryLog(){
 if(!selectedHistoryIdentifier)return;
 const requestedHistoryIdentifier=selectedHistoryIdentifier;
 try{const response=await fetch(historyRoutePrefix+'/jobs/'+requestedHistoryIdentifier);const record=await response.json();if(requestedHistoryIdentifier!==selectedHistoryIdentifier)return;
 const output=document.querySelector('#history-log');output.textContent=response.ok?(record.log||'기록된 로그가 없습니다.'):(record.error||'로그 조회 실패');
 if(document.querySelector('#history-log-details').open)output.scrollTop=output.scrollHeight;
 clearTimeout(historyLogPollTimer);if(['running','queued'].includes(record.status)||['running','queued'].includes(record.status?.status))historyLogPollTimer=setTimeout(loadSelectedHistoryLog,1500);
 }catch(error){document.querySelector('#history-log').textContent=error.message}
}
document.querySelector('#history-log-details').addEventListener('toggle',()=>{const output=document.querySelector('#history-log');if(document.querySelector('#history-log-details').open)output.scrollTop=output.scrollHeight});
document.querySelector('#history-prev').onclick=()=>{currentHistoryPage--;refreshGenerationHistory()};
document.querySelector('#history-next').onclick=()=>{currentHistoryPage++;refreshGenerationHistory()};
const historyRoutePrefix=document.querySelector('#generation-history').dataset.route;
const historyStatusElement=document.querySelector('#history-status');
let historyRequestVersion=0;
function formatHistoryStateLabel(historyStateValue){return ({queued:'GPU 대기 중',running:'생성 중',completed:'완료',cancelled:'취소됨',failed:'실패',missing:'파일 없음'}[historyStateValue]||historyStateValue);}
async function requestSelectedHistoryOperation(historyRecordValue,operationNameValue){
 if(operationNameValue==='resume'&&typeof confirmGpuQueueStart==='function'&&!await confirmGpuQueueStart())return;
 const operationResponse=await fetch(historyRoutePrefix+'/'+operationNameValue,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:historyRecordValue.id})});
 const operationPayload=await operationResponse.json();if(!operationResponse.ok)throw Error(operationPayload.error);
 historyStatusElement.textContent=operationNameValue==='cancel'?'중지를 요청했습니다.':'GPU 대기열에 재개를 요청했습니다.';
 await refreshGenerationHistory();
}
async function deleteSelectedHistoryRecord(historyRecordValue){
 if(!confirm('선택 이력 '+historyRecordValue.id+'을 목록에서 삭제할까요? 결과·입력·로그 파일은 유지됩니다.'))return;
 const deleteResponse=await fetch(historyRoutePrefix+'/history/'+encodeURIComponent(historyRecordValue.id)+'/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:historyRecordValue.id})});
 const deletePayload=await deleteResponse.json();if(!deleteResponse.ok)throw Error(deletePayload.error);
 selectedHistoryIdentifier=null;historyStatusElement.textContent='선택 이력을 목록에서 삭제했습니다. 결과·입력·로그 파일은 유지됩니다.';
 await refreshGenerationHistory();
}
function createSelectedHistoryActions(historyRecordValue){
 const selectedPanelElement=document.createElement('section');selectedPanelElement.className='history-selected-actions';
 const historySummaryElement=document.createElement('p');historySummaryElement.textContent='선택한 작업 · '+formatHistoryStateLabel(historyRecordValue.status.status)+' · '+historyRecordValue.id+' · '+(historyRecordValue.request.kind==='preview'?'웹 3D 프리뷰':'이미지 렌더');selectedPanelElement.append(historySummaryElement);
 const actionGridElement=document.createElement('div');actionGridElement.className='history-selected-action-grid';
 const createActionButton=(buttonLabelValue,buttonActionValue,buttonEnabledValue,primaryActionValue=false)=>{const actionButtonElement=document.createElement('button');actionButtonElement.type='button';actionButtonElement.textContent=buttonLabelValue;actionButtonElement.disabled=!buttonEnabledValue;if(primaryActionValue)actionButtonElement.className='primary';actionButtonElement.onclick=async()=>{actionButtonElement.disabled=true;try{await buttonActionValue();}catch(actionError){historyStatusElement.textContent=actionError.message;}finally{if(document.body.contains(actionButtonElement))actionButtonElement.disabled=!buttonEnabledValue;}};actionGridElement.append(actionButtonElement);};
 const canReadResultValue=historyRecordValue.status.status==='completed'||historyRecordValue.preview_ready;
 createActionButton('결과 조회',async()=>{const historyResultReference=document.querySelector('#history-result-reference');historyResultReference.hidden=false;historyResultReference.textContent='조회한 생성 ID · '+historyRecordValue.id;if(typeof window.showGenerationRecordResult==='function')await window.showGenerationRecordResult(historyRecordValue);else if(typeof window.restoreGenerationRecord==='function')await window.restoreGenerationRecord(historyRecordValue);else if(historyRecordValue.image)showHistoryImageResult(historyRecordValue);},canReadResultValue,true);
 createActionButton('입력값 불러오기',async()=>{if(typeof window.restoreGenerationRecord!=='function')throw Error('이 도구는 입력값 불러오기를 지원하지 않습니다.');await window.restoreGenerationRecord(historyRecordValue);},typeof window.restoreGenerationRecord==='function');
 createActionButton('생성 재개',()=>requestSelectedHistoryOperation(historyRecordValue,'resume'),['failed','cancelled'].includes(historyRecordValue.status.status));
 createActionButton('작업 중지',()=>requestSelectedHistoryOperation(historyRecordValue,'cancel'),['running','queued'].includes(historyRecordValue.status.status));
 if(allowsIndividualHistoryDelete)createActionButton('선택 이력 삭제',()=>deleteSelectedHistoryRecord(historyRecordValue),!['running','queued'].includes(historyRecordValue.status.status));
 selectedPanelElement.append(actionGridElement);return selectedPanelElement;
}
async function refreshGenerationHistory(){
 const currentRequestVersion=++historyRequestVersion;
 try{
  const currentHistoryResponse=await fetch(historyRoutePrefix+'/history');
  const currentHistoryPayload=await currentHistoryResponse.json();
  if(!currentHistoryResponse.ok)throw Error(currentHistoryPayload.error);
  if(currentRequestVersion!==historyRequestVersion)return;
  if(typeof window.onGenerationHistoryUpdated==='function')window.onGenerationHistoryUpdated(currentHistoryPayload);
  const historySearchText=document.querySelector('#history-search').value.trim().toLocaleLowerCase();
  const historyStateValue=document.querySelector('#history-state-filter').value;
  const visibleHistoryRecords=currentHistoryPayload.records.filter(historyRecordValue=>(!historyStateValue||historyRecordValue.status.status===historyStateValue)&&(!historySearchText||JSON.stringify([historyRecordValue.id,historyRecordValue.request]).toLocaleLowerCase().includes(historySearchText)));
  const currentHistoryList=document.querySelector('#history-list');
  const currentOpenRecords=new Set(Array.from(currentHistoryList.querySelectorAll('details[open]')).map(currentOpenElement=>currentOpenElement.dataset.id));currentHistoryList.replaceChildren();
  const historyPageCount=Math.max(1,Math.ceil(visibleHistoryRecords.length/historyPageSize));currentHistoryPage=Math.min(Math.max(1,currentHistoryPage),historyPageCount);
  document.querySelector('#history-page').textContent=currentHistoryPage+' / '+historyPageCount;
  document.querySelector('#history-prev').disabled=currentHistoryPage<=1;document.querySelector('#history-next').disabled=currentHistoryPage>=historyPageCount;
  for(const currentHistoryRecord of visibleHistoryRecords.slice((currentHistoryPage-1)*historyPageSize,currentHistoryPage*historyPageSize)){
   const historyListRow=document.createElement('li');historyListRow.className='history-record-card';historyListRow.classList.toggle('selected',currentHistoryRecord.id===selectedHistoryIdentifier);
   const historyRecordHeader=document.createElement('div');historyRecordHeader.className='history-record-header';historyListRow.append(historyRecordHeader);
   const historyRecordActions=document.createElement('div');historyRecordActions.className='history-record-actions';
   const historyRecordMeta=document.createElement('div');historyRecordMeta.className='history-meta';const historyCreationDate=new Date(currentHistoryRecord.created_at);historyRecordMeta.textContent=Number.isNaN(historyCreationDate.getTime())?currentHistoryRecord.created_at:historyCreationDate.toLocaleString('ko-KR',{hour12:false});historyRecordHeader.append(historyRecordMeta);
   const historyRecordIdentity=document.createElement('code');historyRecordIdentity.className='history-record-id';historyRecordIdentity.textContent=currentHistoryRecord.id;historyListRow.append(historyRecordIdentity);
   for(const [buttonLabel,buttonAction] of [['ID 복사',()=>navigator.clipboard.writeText(currentHistoryRecord.id).then(()=>historyStatusElement.textContent='ID를 복사했습니다.').catch(()=>historyStatusElement.textContent='ID 복사 실패')],['로그 보기',()=>{selectedHistoryIdentifier=currentHistoryRecord.id;document.querySelector('#history-log-details').open=true;document.querySelector('#history-log-details summary').textContent='실행 로그 · '+currentHistoryRecord.id;document.querySelector('#history-log-details').scrollIntoView({behavior:'smooth',block:'nearest'});loadSelectedHistoryLog();refreshGenerationHistory()}]]){const historyActionButton=document.createElement('button');historyActionButton.type='button';historyActionButton.textContent=buttonLabel;historyActionButton.onclick=buttonAction;historyRecordActions.append(historyActionButton)}
   if(['/anny-attributes','/image-generation','/image-generation-2511','/tile-map-generator','/character-animation','/momask-generator'].includes(historyRoutePrefix)){
    for(const [historyActionName,historyActionLabel,historyAllowedStates] of [['cancel','작업 중지',['running','queued']],['resume','생성 재개',['failed','cancelled']]]){
     const historyControlButton=document.createElement('button');historyControlButton.textContent=historyActionLabel;historyControlButton.disabled=!historyAllowedStates.includes(currentHistoryRecord.status.status);
     historyControlButton.onclick=async()=>{historyControlButton.disabled=true;try{if(historyActionName==='resume'&&typeof confirmGpuQueueStart==='function'&&!await confirmGpuQueueStart()){historyControlButton.disabled=false;return;}const historyActionResponse=await fetch(historyRoutePrefix+'/'+historyActionName,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:currentHistoryRecord.id})});const historyActionRecord=await historyActionResponse.json();if(!historyActionResponse.ok)throw new Error(historyActionRecord.error);historyStatusElement.textContent=historyActionName==='cancel'?'중지를 요청했습니다.':'GPU 대기열에 재개를 요청했습니다.';await refreshGenerationHistory();}catch(historyActionError){historyStatusElement.textContent=historyActionError.message;historyControlButton.disabled=false;}};
     historyRecordActions.append(historyControlButton);
    }
   }
   if(currentHistoryRecord.path){
    const historyFolderContainer=document.createElement('div');historyFolderContainer.className='history-record-folder';
    const historyFolderPath=document.createElement('code');historyFolderPath.textContent=currentHistoryRecord.path;historyFolderContainer.append(historyFolderPath);
    const historyFolderCopy=document.createElement('button');historyFolderCopy.type='button';historyFolderCopy.textContent='경로 복사';historyFolderCopy.onclick=()=>navigator.clipboard.writeText(currentHistoryRecord.path).then(()=>historyStatusElement.textContent='기록 폴더 경로를 복사했습니다.').catch(()=>historyStatusElement.textContent='경로 복사 실패 · 표시된 경로를 직접 복사하세요.');historyFolderContainer.append(historyFolderCopy);
    const historyFolderButton=document.createElement('button');historyFolderButton.type='button';historyFolderButton.textContent='기록 폴더 열기 ↗';historyFolderButton.title='관리도구를 실행 중인 컴퓨터의 파일 관리자에서 엽니다.';
    historyFolderButton.onclick=async()=>{historyFolderButton.disabled=true;try{const folderOpenResponse=await fetch('/management/record-folder/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({route:historyRoutePrefix,id:currentHistoryRecord.id})});const folderOpenPayload=await folderOpenResponse.json();if(!folderOpenResponse.ok)throw Error(folderOpenPayload.error);historyStatusElement.textContent=folderOpenPayload.message;}catch(folderOpenError){historyStatusElement.textContent=folderOpenError.message;}finally{historyFolderButton.disabled=false;}};historyFolderContainer.append(historyFolderButton);historyListRow.append(historyFolderContainer);
   }
   const historyStateLabel=document.createElement('span');historyStateLabel.className='history-state-label';historyStateLabel.dataset.state=currentHistoryRecord.status.status;historyStateLabel.textContent=formatHistoryStateLabel(currentHistoryRecord.status.status);historyRecordHeader.prepend(historyStateLabel);
   const currentHistoryArticle=document.createElement('details');currentHistoryArticle.dataset.id=currentHistoryRecord.id;currentHistoryArticle.open=currentOpenRecords.has(currentHistoryRecord.id);
   const currentHistorySummary=document.createElement('summary');
   currentHistorySummary.textContent=currentHistoryRecord.request.attributes?'속성 · 렌더링 설정':'입력 내용';
   const historyInputSummary=document.createElement('p');historyInputSummary.className='history-input-summary';
   const historyDirectionLabels={down_left:'전방 좌측',down_right:'전방 우측',up_left:'후방 좌측',up_right:'후방 우측'};
   historyInputSummary.textContent=currentHistoryRecord.request.motion?[currentHistoryRecord.request.motion,(currentHistoryRecord.request.resolution||512)+'px',currentHistoryRecord.request.character,currentHistoryRecord.request.source==='openpose'?'OpenPose':'ANNY',(currentHistoryRecord.request.directions||[]).map(directionNameValue=>historyDirectionLabels[directionNameValue]||directionNameValue).join(' · '),(currentHistoryRecord.request.speed||1)+'배 생성',(currentHistoryRecord.request.target_fps?'타겟 '+currentHistoryRecord.request.target_fps+' FPS':(currentHistoryRecord.request.frame_step||1)+'프레임 간격'),(currentHistoryRecord.request.steps||4)+'스텝'].join(' / '):currentHistoryRecord.request.attributes?['ANNY',currentHistoryRecord.request.kind==='preview'?'웹 3D 프리뷰':'이미지 렌더','Y축 '+(currentHistoryRecord.request.render_settings?.rotation_y??currentHistoryRecord.request.attributes.rotation_y??0)+'°'].join(' · '):(currentHistoryRecord.request.steps||4)+'스텝'+(currentHistoryRecord.request.width?' · '+currentHistoryRecord.request.width+' × '+currentHistoryRecord.request.height:'');
   if(currentHistoryRecord.request.action&&historyRoutePrefix==='/momask-generator')historyInputSummary.textContent=({standing:'대기',deep_breath:'심호흡',stretch:'스트레칭',walking:'걷기',resting:'휴식'}[currentHistoryRecord.request.action]||currentHistoryRecord.request.action)+' · '+currentHistoryRecord.request.frames+'프레임 · '+(currentHistoryRecord.request.directions||[]).map(value=>historyDirectionLabels[value]||value).join(' · ');
   if(currentHistoryRecord.request.tile_type)historyInputSummary.textContent=({rooftop:'지붕 타일',wall:'벽 타일·문 포함',ground:'바닥 타일'}[currentHistoryRecord.request.tile_type]||currentHistoryRecord.request.tile_type)+' / '+historyInputSummary.textContent;
   historyRecordIdentity.after(historyInputSummary);
   if(currentHistoryRecord.request.tile_type)currentHistorySummary.textContent='생성 프롬프트 · '+currentHistoryRecord.request.prompt_words+'단어';
   currentHistoryArticle.append(currentHistorySummary);
   const currentPromptElement=document.createElement('pre');currentPromptElement.textContent=currentHistoryRecord.request.attributes?JSON.stringify(currentHistoryRecord.request.attributes,null,2):currentHistoryRecord.request.prompt||(historyRoutePrefix==='/momask-generator'?JSON.stringify(currentHistoryRecord.request,null,2):currentHistoryRecord.request.motion?'등록 에셋 · 고정 프롬프트 사용':'모델 준비');currentHistoryArticle.append(currentPromptElement);
   if(currentHistoryRecord.request.motion){
    const historyRequestValue=currentHistoryRecord.request;
    const historyInputDetails=document.createElement('pre');
    const historyInputLines=[
     '출력 해상도: '+(historyRequestValue.resolution||512)+' × '+(historyRequestValue.resolution||512),
     '모델: '+(historyRequestValue.model||'기록 없음'),
     '생성 방식: '+(historyRequestValue.steps||4)+'스텝 · '+((historyRequestValue.steps||4)===4?'Lightning':'표준'),
     '원본: '+(historyRequestValue.source_frames_per_direction??'기록 없음')+'프레임 / '+(historyRequestValue.source_fps??'기록 없음')+' FPS',
     '생성: 방향당 '+(historyRequestValue.frames_per_direction??'기록 없음')+'장 / 총 '+(historyRequestValue.frames?.length??'기록 없음')+'장',
     '선택한 원본 프레임: '+(historyRequestValue.selected_frame_numbers||[]).join(', '),
     '모션 매니페스트 SHA-256: '+(historyRequestValue.motion_manifest_sha256||'기록 없음'),
     '캐릭터 매니페스트 SHA-256: '+(historyRequestValue.character_manifest_sha256||'기록 없음')
    ];
    const historyReferencePaths=[...new Set((historyRequestValue.frames||[]).map(frameRecordValue=>frameRecordValue.character_path))].filter(Boolean);
    historyInputLines.push('캐릭터 참조 경로:\n'+historyReferencePaths.join('\n'));
    historyInputDetails.textContent=historyInputLines.join('\n');currentHistoryArticle.append(historyInputDetails);
    currentPromptElement.textContent=Object.entries(historyRequestValue.prompts||{}).map(([promptRoleName,promptTextValue])=>promptRoleName+' · '+promptTextValue.trim().split(/\s+/).length+'단어\n'+promptTextValue).join('\n\n')||'프롬프트 기록 없음';
    for(const directionNameValue of historyRequestValue.directions||[]){
     const directionPromptValue=historyRequestValue.direction_prompts?.[directionNameValue];
     if(!directionPromptValue)continue;
     const directionPromptDetails=document.createElement('details');
     const directionPromptSummary=document.createElement('summary');directionPromptSummary.textContent=(historyDirectionLabels[directionNameValue]||directionNameValue)+' 실제 입력 · '+directionPromptValue.words+'단어';
     const directionPromptContent=document.createElement('pre');directionPromptContent.textContent=directionPromptValue.text+'\nSHA-256: '+directionPromptValue.sha256;
     directionPromptDetails.append(directionPromptSummary,directionPromptContent);currentHistoryArticle.append(directionPromptDetails);
    }
   }
   if(currentHistoryRecord.request.render_settings){const historyRenderSettings=document.createElement('p');historyRenderSettings.textContent='렌더링 설정 · Y축 회전 '+currentHistoryRecord.request.render_settings.rotation_y+'°';currentHistoryArticle.append(historyRenderSettings)}
   if(currentHistoryRecord.request.prompt){const currentReuseButton=document.createElement('button');currentReuseButton.type='button';currentReuseButton.textContent='입력값 다시 불러오기';currentReuseButton.onclick=async()=>{currentReuseButton.disabled=true;try{if(typeof restoreReferenceInputs==='function')await restoreReferenceInputs(currentHistoryRecord);document.querySelector('#prompt').value=currentHistoryRecord.request.user_prompt??currentHistoryRecord.request.prompt;if(currentHistoryRecord.request.tile_type){document.querySelector('#tile-type').value=currentHistoryRecord.request.tile_type;document.querySelector('#tile-type').dispatchEvent(new Event('change'));}document.querySelector('#seed').value=currentHistoryRecord.request.seed??((historyRoutePrefix.endsWith('2511')||historyRoutePrefix==='/tile-map-generator')?10107:251204);const currentInputMode=document.querySelector('#input-mode');if(currentInputMode&&currentHistoryRecord.request.references){currentInputMode.value=currentHistoryRecord.request.references.length?'references':'text';currentInputMode.dispatchEvent(new Event('change'));}const currentResolutionSelect=document.querySelector('#resolution');if(currentResolutionSelect&&currentHistoryRecord.request.width){const currentResolutionValue=currentHistoryRecord.request.width+'x'+currentHistoryRecord.request.height;if(!Array.from(currentResolutionSelect.options).some(currentResolutionOption=>currentResolutionOption.value===currentResolutionValue))currentResolutionSelect.add(new Option(currentResolutionValue,currentResolutionValue));currentResolutionSelect.value=currentResolutionValue;}for(const currentSettingName of ['steps','width','height']){const currentSettingElement=document.querySelector('#'+currentSettingName);if(currentSettingElement&&currentHistoryRecord.request[currentSettingName])currentSettingElement.value=currentHistoryRecord.request[currentSettingName];}await synchronizeGenerationAvailability();historyStatusElement.textContent='입력값을 복원했습니다. 수정 후 생성 버튼을 누르세요.';document.querySelector('#generate').scrollIntoView({behavior:'smooth',block:'start'});document.querySelector('#prompt').focus({preventScroll:true});}catch(currentRestoreError){historyStatusElement.textContent='불러오기 실패: '+currentRestoreError.message;}finally{currentReuseButton.disabled=false;}};historyRecordActions.append(currentReuseButton);}
   if(currentHistoryRecord.request.attributes&&typeof window.restoreGenerationRecord==='function'){const historyReplayButton=document.createElement('button');historyReplayButton.textContent='결과 보기 · 입력 복원';historyReplayButton.disabled=currentHistoryRecord.status.status!=='completed'&&!currentHistoryRecord.preview_ready;historyReplayButton.className='primary';historyReplayButton.onclick=async()=>{historyReplayButton.disabled=true;try{await window.restoreGenerationRecord(currentHistoryRecord);selectedHistoryIdentifier=currentHistoryRecord.id;for(const selectedHistoryRow of document.querySelectorAll('#history-list>li'))selectedHistoryRow.classList.toggle('selected',selectedHistoryRow===historyListRow);}catch(historyRestoreError){historyStatusElement.textContent='결과 조회 실패: '+historyRestoreError.message;}finally{historyReplayButton.disabled=false;}};historyRecordActions.append(historyReplayButton);}
   if(['cancelled','failed'].includes(currentHistoryRecord.status.status)&&typeof window.resumeGenerationRecord==='function'){const historyResumeButton=document.createElement('button');historyResumeButton.textContent='이어서 생성';historyResumeButton.onclick=async()=>{historyResumeButton.disabled=true;try{await window.resumeGenerationRecord(currentHistoryRecord);await refreshGenerationHistory();}catch(resumeRequestError){historyResumeButton.disabled=false;document.getElementById('history-status').textContent=resumeRequestError.message;}};historyRecordActions.append(historyResumeButton);}
   if(currentHistoryRecord.playable&&typeof window.playGenerationRecord==='function'){const historyPlaybackButton=document.createElement('button');historyPlaybackButton.textContent='결과 보기 · 재생';historyPlaybackButton.className='primary';historyPlaybackButton.onclick=()=>{selectedHistoryIdentifier=currentHistoryRecord.id;for(const historySelectedRow of document.querySelectorAll('#history-list>li'))historySelectedRow.classList.toggle('selected',historySelectedRow===historyListRow);window.playGenerationRecord(currentHistoryRecord);};historyRecordActions.append(historyPlaybackButton);}
   const historyThumbnailUrl=currentHistoryRecord.thumbnail||currentHistoryRecord.image||(currentHistoryRecord.preview_ready&&currentHistoryRecord.request.attributes?historyRoutePrefix+'/jobs/'+encodeURIComponent(currentHistoryRecord.id)+'/front.png':null);
   if(currentHistoryRecord.status.status==='completed'&&historyThumbnailUrl){const thumbnailImage=document.createElement('img');thumbnailImage.className='generation-history-thumbnail';thumbnailImage.alt='완료 결과 미리보기 · '+currentHistoryRecord.id;thumbnailImage.loading='lazy';thumbnailImage.decoding='async';thumbnailImage.width=112;thumbnailImage.height=112;thumbnailImage.src=historyThumbnailUrl;thumbnailImage.onerror=()=>thumbnailImage.replaceWith(document.createTextNode('미리보기 파일 없음'));historyListRow.prepend(thumbnailImage);historyListRow.classList.add('has-thumbnail');}
   if(currentHistoryRecord.image){const currentResultButton=document.createElement('button');currentResultButton.type='button';currentResultButton.textContent='결과 보기';currentResultButton.onclick=()=>showHistoryImageResult(currentHistoryRecord);historyRecordActions.append(currentResultButton);}

   if(currentHistoryRecord.status.error){const currentErrorElement=document.createElement('p');currentErrorElement.textContent=currentHistoryRecord.status.error;currentErrorElement.className='error';historyListRow.append(currentErrorElement);}
   const historyFolderDetails=historyListRow.querySelector('.history-record-folder');if(historyFolderDetails){currentHistoryArticle.append(historyFolderDetails);currentHistorySummary.textContent+=' · 기록 경로';}
   historyInputSummary.after(historyRecordActions);historyListRow.append(currentHistoryArticle);
   if(usesSelectionActions){
    historyListRow.tabIndex=0;historyListRow.setAttribute('role','button');historyListRow.setAttribute('aria-pressed',String(currentHistoryRecord.id===selectedHistoryIdentifier));
    const selectCurrentHistoryRecord=()=>{selectedHistoryIdentifier=currentHistoryRecord.id;loadSelectedHistoryLog();refreshGenerationHistory();};
    historyListRow.addEventListener('click',clickEvent=>{if(clickEvent.target.closest('button,a,input,summary'))return;selectCurrentHistoryRecord();});
    historyListRow.addEventListener('keydown',keyboardEvent=>{if(keyboardEvent.key==='Enter'||keyboardEvent.key===' '){keyboardEvent.preventDefault();selectCurrentHistoryRecord();}});
    if(currentHistoryRecord.id===selectedHistoryIdentifier)historyListRow.append(createSelectedHistoryActions(currentHistoryRecord));
   }
   currentHistoryList.append(historyListRow);
  }
  historyStatusElement.textContent='전체 '+currentHistoryPayload.records.length+'건 · 표시 '+visibleHistoryRecords.length+'건 · 최신순';
  if(!visibleHistoryRecords.length){const emptyHistoryMessage=document.createElement('li');emptyHistoryMessage.textContent=currentHistoryPayload.records.length?'조건에 맞는 이력이 없습니다. 검색어나 상태 필터를 변경하세요.':'아직 생성 이력이 없습니다. 작업을 생성하면 이곳에서 결과를 다시 확인할 수 있습니다.';currentHistoryList.append(emptyHistoryMessage);}
 }catch(currentHistoryError){historyStatusElement.textContent=currentHistoryError.message;}
}
let historySearchTimer=null;
document.querySelector('#history-search').oninput=()=>{clearTimeout(historySearchTimer);historySearchTimer=setTimeout(()=>{currentHistoryPage=1;refreshGenerationHistory();},250);};
document.querySelector('#history-state-filter').onchange=()=>{currentHistoryPage=1;refreshGenerationHistory();};
document.querySelector('#history-refresh').onclick=refreshGenerationHistory;
document.querySelector('#history-reset').onclick=async()=>{
 if(!confirm(generationHistoryContainer.dataset.resetDeletesFiles==='true'?'이 생성기의 전체 이력과 참조 이미지·결과·로그 파일을 삭제할까요? 정식 등록 에셋은 유지됩니다.':'이 생성기의 프롬프트·이력 목록을 초기화할까요? 실험 폴더의 입력과 결과 파일은 유지됩니다.'))return;
 try{const currentResetResponse=await fetch(historyRoutePrefix+'/history/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'reset'})});const currentResetPayload=await currentResetResponse.json();if(!currentResetResponse.ok)throw Error(currentResetPayload.error);document.dispatchEvent(new CustomEvent('generation-history-reset',{detail:{route:historyRoutePrefix}}));document.querySelector('#history-image-dialog')?.close();currentHistoryPage=1;selectedHistoryIdentifier=null;clearTimeout(historyLogPollTimer);document.querySelector('#history-log').textContent='이력에서 로그 보기를 선택하세요.';document.querySelector('#history-log-details').open=false;await refreshGenerationHistory();}catch(currentResetError){historyStatusElement.textContent=currentResetError.message;}
};
refreshGenerationHistory();
setInterval(refreshGenerationHistory,10000);

// 이미지 생성기에서 같은 결과 보기 화면을 사용한다. 실행 중인 작업 상태는 바꾸지 않는다.
function showHistoryImageResult(historyRecordValue){
 let resultDialogElement=document.querySelector('#history-image-dialog');
 if(!resultDialogElement){
  resultDialogElement=document.createElement('dialog');resultDialogElement.id='history-image-dialog';resultDialogElement.className='studio-panel';resultDialogElement.style.cssText='width:min(900px,90vw);max-height:90vh;overflow:auto';
  resultDialogElement.innerHTML='<h2>생성 결과</h2><p data-result-description></p><p data-result-status role="status"></p><div class="generation-result-images"><section><h3>생성 원본</h3><img data-result-image alt="생성 원본"></section><section data-result-crop-section hidden><h3>보더 크롭 결과</h3><p data-result-crop-status role="status"></p><a data-result-crop-link target="_blank" rel="noopener"><img data-result-crop-image alt="보더 크롭 결과"></a></section></div><div class="generation-actions"><a data-result-original target="_blank" rel="noopener">원본 이미지 열기</a><button type="button" data-result-close>닫기</button></div>';
  document.body.append(resultDialogElement);resultDialogElement.querySelector('[data-result-close]').onclick=()=>resultDialogElement.close();
 }
 const resultImageElement=resultDialogElement.querySelector('[data-result-image]');
 resultDialogElement.querySelector('[data-result-description]').textContent=historyRecordValue.id+' · '+(historyRecordValue.request.tile_type||'이미지');
 const resultStatusElement=resultDialogElement.querySelector('[data-result-status]');resultStatusElement.textContent='이미지를 불러오는 중…';
 resultImageElement.onload=()=>{resultStatusElement.textContent=resultImageElement.naturalWidth+' × '+resultImageElement.naturalHeight+' px';};
 resultImageElement.onerror=()=>{resultStatusElement.textContent='결과 이미지를 불러오지 못했습니다. 기록 파일을 확인하세요.';};
 resultImageElement.src=historyRecordValue.image;
 resultDialogElement.querySelector('[data-result-original]').href=historyRecordValue.image;
 const croppedResultSection=resultDialogElement.querySelector('[data-result-crop-section]');
 const croppedResultImage=resultDialogElement.querySelector('[data-result-crop-image]');
 const croppedResultStatus=resultDialogElement.querySelector('[data-result-crop-status]');
 croppedResultSection.hidden=!historyRecordValue.cropped_image;
 if(historyRecordValue.cropped_image){
  croppedResultStatus.textContent='크롭 이미지를 불러오는 중…';
  croppedResultImage.onload=()=>{croppedResultStatus.textContent=croppedResultImage.naturalWidth+' × '+croppedResultImage.naturalHeight+' px';};
  croppedResultImage.onerror=()=>{croppedResultStatus.textContent='크롭 이미지를 불러오지 못했습니다. 기록 파일을 확인하세요.';};
  croppedResultImage.src=historyRecordValue.cropped_image;
  resultDialogElement.querySelector('[data-result-crop-link]').href=historyRecordValue.cropped_image;
 }else{
  croppedResultImage.removeAttribute('src');
  resultDialogElement.querySelector('[data-result-crop-link]').removeAttribute('href');
  croppedResultStatus.textContent='';
 }

 if(!resultDialogElement.open)resultDialogElement.showModal();
}
