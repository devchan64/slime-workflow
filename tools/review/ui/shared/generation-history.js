// 생성기별 페이지는 빈 컨테이너와 API 경로만 제공한다. 이력 UI는 이 파일에서 공통 관리한다.
const generationHistoryContainer=document.querySelector('#generation-history');
generationHistoryContainer.innerHTML='<div class="history-heading"><div><h2>생성 이력</h2><p>결과는 누적 보관됩니다. 목록 초기화는 수동으로 실행하며 원본 파일은 유지됩니다.</p></div><div class="history-management-actions"><button type="button" id="history-refresh">이력 새로고침</button> <button type="button" id="history-reset">이력 수동 초기화</button></div></div><div class="history-filters"><label>이력 검색<input id="history-search" type="search" placeholder="ID·모션·프롬프트 검색"></label><label>작업 상태<select id="history-state-filter"><option value="">전체 상태</option><option value="completed">완료</option><option value="running">생성 중</option><option value="failed">실패</option><option value="cancelled">취소됨</option></select></label></div><p id="history-status" role="status"></p><ul id="history-list"></ul><div class="history-pager"><button id="history-prev" type="button">← 이전</button> <span id="history-page"></span> <button id="history-next" type="button">다음 →</button></div><details id="history-log-details"><summary>선택한 작업 로그</summary><pre id="history-log">이력에서 로그 보기를 선택하세요.</pre></details>';
let currentHistoryPage=1,selectedHistoryIdentifier=null,historyLogPollTimer=null;
const historyPageSize=8;
async function loadSelectedHistoryLog(){
 if(!selectedHistoryIdentifier)return;
 const requestedHistoryIdentifier=selectedHistoryIdentifier;
 try{const response=await fetch(historyRoutePrefix+'/jobs/'+requestedHistoryIdentifier);const record=await response.json();if(requestedHistoryIdentifier!==selectedHistoryIdentifier)return;
 const output=document.querySelector('#history-log');output.textContent=response.ok?(record.log||'기록된 로그가 없습니다.'):(record.error||'로그 조회 실패');
 if(document.querySelector('#history-log-details').open)output.scrollTop=output.scrollHeight;
 clearTimeout(historyLogPollTimer);if(record.status==='running'||record.status?.status==='running')historyLogPollTimer=setTimeout(loadSelectedHistoryLog,1500);
 }catch(error){document.querySelector('#history-log').textContent=error.message}
}
document.querySelector('#history-log-details').addEventListener('toggle',()=>{const output=document.querySelector('#history-log');if(document.querySelector('#history-log-details').open)output.scrollTop=output.scrollHeight});
document.querySelector('#history-prev').onclick=()=>{currentHistoryPage--;refreshGenerationHistory()};
document.querySelector('#history-next').onclick=()=>{currentHistoryPage++;refreshGenerationHistory()};
const historyRoutePrefix=document.querySelector('#generation-history').dataset.route;
const historyStatusElement=document.querySelector('#history-status');
let historyRequestVersion=0;
async function refreshGenerationHistory(){
 const currentRequestVersion=++historyRequestVersion;
 try{
  const currentHistoryResponse=await fetch(historyRoutePrefix+'/history');
  const currentHistoryPayload=await currentHistoryResponse.json();
  if(!currentHistoryResponse.ok)throw Error(currentHistoryPayload.error);
  if(currentRequestVersion!==historyRequestVersion)return;
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
   if(currentHistoryRecord.path){
    const historyFolderContainer=document.createElement('div');historyFolderContainer.className='history-record-folder';
    const historyFolderPath=document.createElement('code');historyFolderPath.textContent=currentHistoryRecord.path;historyFolderContainer.append(historyFolderPath);
    const historyFolderCopy=document.createElement('button');historyFolderCopy.type='button';historyFolderCopy.textContent='경로 복사';historyFolderCopy.onclick=()=>navigator.clipboard.writeText(currentHistoryRecord.path).then(()=>historyStatusElement.textContent='기록 폴더 경로를 복사했습니다.').catch(()=>historyStatusElement.textContent='경로 복사 실패 · 표시된 경로를 직접 복사하세요.');historyFolderContainer.append(historyFolderCopy);
    const historyFolderButton=document.createElement('button');historyFolderButton.type='button';historyFolderButton.textContent='기록 폴더 열기 ↗';historyFolderButton.title='관리도구를 실행 중인 컴퓨터의 파일 관리자에서 엽니다.';
    historyFolderButton.onclick=async()=>{historyFolderButton.disabled=true;try{const folderOpenResponse=await fetch('/management/record-folder/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({route:historyRoutePrefix,id:currentHistoryRecord.id})});const folderOpenPayload=await folderOpenResponse.json();if(!folderOpenResponse.ok)throw Error(folderOpenPayload.error);historyStatusElement.textContent=folderOpenPayload.message;}catch(folderOpenError){historyStatusElement.textContent=folderOpenError.message;}finally{historyFolderButton.disabled=false;}};historyFolderContainer.append(historyFolderButton);historyListRow.append(historyFolderContainer);
   }
   const historyStateLabel=document.createElement('span');historyStateLabel.className='history-state-label';historyStateLabel.dataset.state=currentHistoryRecord.status.status;historyStateLabel.textContent=({running:'생성 중',completed:'완료',cancelled:'취소됨',failed:'실패',missing:'파일 없음'}[currentHistoryRecord.status.status]||currentHistoryRecord.status.status);historyRecordHeader.prepend(historyStateLabel);
   const currentHistoryArticle=document.createElement('details');currentHistoryArticle.dataset.id=currentHistoryRecord.id;currentHistoryArticle.open=currentOpenRecords.has(currentHistoryRecord.id);
   const currentHistorySummary=document.createElement('summary');
   currentHistorySummary.textContent=currentHistoryRecord.request.attributes?'속성 · 렌더링 설정':'입력 내용';
   const historyInputSummary=document.createElement('p');historyInputSummary.className='history-input-summary';
   const historyDirectionLabels={down_left:'전방 좌측',down_right:'전방 우측',up_left:'후방 좌측',up_right:'후방 우측'};
   historyInputSummary.textContent=currentHistoryRecord.request.motion?[currentHistoryRecord.request.motion,currentHistoryRecord.request.character,currentHistoryRecord.request.source==='openpose'?'OpenPose':'ANNY',(currentHistoryRecord.request.directions||[]).map(directionNameValue=>historyDirectionLabels[directionNameValue]||directionNameValue).join(' · '),(currentHistoryRecord.request.frame_step||1)+'프레임 간격',(currentHistoryRecord.request.steps||4)+'스텝'].join(' / '):currentHistoryRecord.request.attributes?'ANNY · 캐릭터 속성 렌더링':(currentHistoryRecord.request.steps||4)+'스텝'+(currentHistoryRecord.request.width?' · '+currentHistoryRecord.request.width+' × '+currentHistoryRecord.request.height:'');
   historyRecordIdentity.after(historyInputSummary);
   currentHistoryArticle.append(currentHistorySummary);
   const currentPromptElement=document.createElement('pre');currentPromptElement.textContent=currentHistoryRecord.request.attributes?JSON.stringify(currentHistoryRecord.request.attributes,null,2):currentHistoryRecord.request.prompt||(currentHistoryRecord.request.motion?'등록 에셋 · 고정 프롬프트 사용':'모델 준비');currentHistoryArticle.append(currentPromptElement);
   if(currentHistoryRecord.request.render_settings){const historyRenderSettings=document.createElement('p');historyRenderSettings.textContent='렌더링 설정 · Y축 회전 '+currentHistoryRecord.request.render_settings.rotation_y+'°';currentHistoryArticle.append(historyRenderSettings)}
   if(currentHistoryRecord.request.prompt){const currentReuseButton=document.createElement('button');currentReuseButton.type='button';currentReuseButton.textContent='입력값 다시 불러오기';currentReuseButton.onclick=async()=>{currentReuseButton.disabled=true;try{if(typeof restoreReferenceInputs==='function')await restoreReferenceInputs(currentHistoryRecord);document.querySelector('#prompt').value=currentHistoryRecord.request.prompt;document.querySelector('#seed').value=currentHistoryRecord.request.seed??(historyRoutePrefix.endsWith('2511')?10107:251204);const currentInputMode=document.querySelector('#input-mode');if(currentInputMode&&currentHistoryRecord.request.references){currentInputMode.value=currentHistoryRecord.request.references.length?'references':'text';currentInputMode.dispatchEvent(new Event('change'));}const currentResolutionSelect=document.querySelector('#resolution');if(currentResolutionSelect&&currentHistoryRecord.request.width){const currentResolutionValue=currentHistoryRecord.request.width+'x'+currentHistoryRecord.request.height;if(!Array.from(currentResolutionSelect.options).some(currentResolutionOption=>currentResolutionOption.value===currentResolutionValue))currentResolutionSelect.add(new Option(currentResolutionValue,currentResolutionValue));currentResolutionSelect.value=currentResolutionValue;}for(const currentSettingName of ['steps','width','height']){const currentSettingElement=document.querySelector('#'+currentSettingName);if(currentSettingElement&&currentHistoryRecord.request[currentSettingName])currentSettingElement.value=currentHistoryRecord.request[currentSettingName];}await synchronizeGenerationAvailability();historyStatusElement.textContent='입력값을 복원했습니다. 수정 후 생성 버튼을 누르세요.';document.querySelector('#generate').scrollIntoView({behavior:'smooth',block:'start'});document.querySelector('#prompt').focus({preventScroll:true});}catch(currentRestoreError){historyStatusElement.textContent='불러오기 실패: '+currentRestoreError.message;}finally{currentReuseButton.disabled=false;}};historyRecordActions.append(currentReuseButton);}
   if(currentHistoryRecord.request.attributes&&typeof window.restoreGenerationRecord==='function'){const historyReplayButton=document.createElement('button');historyReplayButton.textContent='결과 보기 · 입력 복원';historyReplayButton.disabled=currentHistoryRecord.status.status!=='completed'&&!currentHistoryRecord.preview_ready;historyReplayButton.onclick=()=>window.restoreGenerationRecord(currentHistoryRecord);historyRecordActions.append(historyReplayButton);}
   if(currentHistoryRecord.playable&&typeof window.playGenerationRecord==='function'){const historyPlaybackButton=document.createElement('button');historyPlaybackButton.textContent='결과 보기 · 재생';historyPlaybackButton.className='primary';historyPlaybackButton.onclick=()=>{selectedHistoryIdentifier=currentHistoryRecord.id;for(const historySelectedRow of document.querySelectorAll('#history-list>li'))historySelectedRow.classList.toggle('selected',historySelectedRow===historyListRow);window.playGenerationRecord(currentHistoryRecord);};historyRecordActions.append(historyPlaybackButton);}
   if(currentHistoryRecord.image){const currentResultLink=document.createElement('a');currentResultLink.href=currentHistoryRecord.image;currentResultLink.target='_blank';currentResultLink.rel='noopener';currentResultLink.textContent='결과 보기';historyRecordActions.append(currentResultLink);}
   if(currentHistoryRecord.status.error){const currentErrorElement=document.createElement('p');currentErrorElement.textContent=currentHistoryRecord.status.error;currentErrorElement.className='error';historyListRow.append(currentErrorElement);}
   historyInputSummary.after(historyRecordActions);historyListRow.append(currentHistoryArticle);currentHistoryList.append(historyListRow);
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
 if(!confirm('이 생성기의 프롬프트·이력 목록을 초기화할까요? 실험 폴더의 입력과 결과 파일은 유지됩니다.'))return;
 try{const currentResetResponse=await fetch(historyRoutePrefix+'/history/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'reset'})});const currentResetPayload=await currentResetResponse.json();if(!currentResetResponse.ok)throw Error(currentResetPayload.error);await refreshGenerationHistory();}catch(currentResetError){historyStatusElement.textContent=currentResetError.message;}
};
refreshGenerationHistory();
setInterval(refreshGenerationHistory,10000);
