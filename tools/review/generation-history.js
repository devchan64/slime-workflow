const historyRoutePrefix=document.querySelector('#generation-history').dataset.route;
const historyStatusElement=document.querySelector('#history-status');
async function refreshGenerationHistory(){
 try{
  const currentHistoryResponse=await fetch(historyRoutePrefix+'/history');
  const currentHistoryPayload=await currentHistoryResponse.json();
  if(!currentHistoryResponse.ok)throw Error(currentHistoryPayload.error);
  const currentHistoryList=document.querySelector('#history-list');
  const currentOpenRecords=new Set(Array.from(currentHistoryList.querySelectorAll('details[open]')).map(currentOpenElement=>currentOpenElement.dataset.id));currentHistoryList.replaceChildren();
  for(const currentHistoryRecord of currentHistoryPayload.records){
   const currentHistoryArticle=document.createElement('details');currentHistoryArticle.dataset.id=currentHistoryRecord.id;currentHistoryArticle.open=currentOpenRecords.has(currentHistoryRecord.id);
   const currentHistorySummary=document.createElement('summary');
   currentHistorySummary.textContent=currentHistoryRecord.created_at+' · '+({running:'생성 중',completed:'완료',cancelled:'취소됨',failed:'실패',missing:'파일 없음'}[currentHistoryRecord.status.status]||currentHistoryRecord.status.status)+' · '+(currentHistoryRecord.request.attributes?'ANNY 속성':(currentHistoryRecord.request.steps||4)+'스텝');
   currentHistoryArticle.append(currentHistorySummary);
   const currentPromptElement=document.createElement('pre');currentPromptElement.textContent=currentHistoryRecord.request.attributes?JSON.stringify(currentHistoryRecord.request.attributes,null,2):currentHistoryRecord.request.prompt||'모델 준비';currentHistoryArticle.append(currentPromptElement);
   if(currentHistoryRecord.request.prompt){const currentReuseButton=document.createElement('button');currentReuseButton.type='button';currentReuseButton.textContent='입력값 다시 불러오기';currentReuseButton.onclick=async()=>{currentReuseButton.disabled=true;try{if(typeof restoreReferenceInputs==='function')await restoreReferenceInputs(currentHistoryRecord);document.querySelector('#prompt').value=currentHistoryRecord.request.prompt;document.querySelector('#seed').value=currentHistoryRecord.request.seed??(historyRoutePrefix.endsWith('2511')?10107:251204);const currentInputMode=document.querySelector('#input-mode');if(currentInputMode&&currentHistoryRecord.request.references){currentInputMode.value=currentHistoryRecord.request.references.length?'references':'text';currentInputMode.dispatchEvent(new Event('change'));}const currentResolutionSelect=document.querySelector('#resolution');if(currentResolutionSelect&&currentHistoryRecord.request.width){const currentResolutionValue=currentHistoryRecord.request.width+'x'+currentHistoryRecord.request.height;if(!Array.from(currentResolutionSelect.options).some(currentResolutionOption=>currentResolutionOption.value===currentResolutionValue))currentResolutionSelect.add(new Option(currentResolutionValue,currentResolutionValue));currentResolutionSelect.value=currentResolutionValue;}for(const currentSettingName of ['steps','width','height']){const currentSettingElement=document.querySelector('#'+currentSettingName);if(currentSettingElement&&currentHistoryRecord.request[currentSettingName])currentSettingElement.value=currentHistoryRecord.request[currentSettingName];}await synchronizeGenerationAvailability();historyStatusElement.textContent='입력값을 복원했습니다. 수정 후 생성 버튼을 누르세요.';document.querySelector('#generate').scrollIntoView({behavior:'smooth',block:'start'});document.querySelector('#prompt').focus({preventScroll:true});}catch(currentRestoreError){historyStatusElement.textContent='불러오기 실패: '+currentRestoreError.message;}finally{currentReuseButton.disabled=false;}};currentHistoryArticle.append(currentReuseButton);}
   if(currentHistoryRecord.request.attributes&&typeof window.restoreGenerationRecord==='function'){const historyReplayButton=document.createElement('button');historyReplayButton.textContent='결과 재생 · 입력 복원';historyReplayButton.disabled=currentHistoryRecord.status.status!=='completed';historyReplayButton.onclick=()=>window.restoreGenerationRecord(currentHistoryRecord);currentHistoryArticle.append(historyReplayButton);}
   if(currentHistoryRecord.image){const currentResultLink=document.createElement('a');currentResultLink.href=currentHistoryRecord.image;currentResultLink.target='_blank';currentResultLink.rel='noopener';currentResultLink.textContent='결과 보기';currentHistoryArticle.append(currentResultLink);}
   if(currentHistoryRecord.status.error){const currentErrorElement=document.createElement('p');currentErrorElement.textContent=currentHistoryRecord.status.error;currentHistoryArticle.append(currentErrorElement);}
   currentHistoryList.append(currentHistoryArticle);
  }
  historyStatusElement.textContent=currentHistoryPayload.records.length+'개 기록';
 }catch(currentHistoryError){historyStatusElement.textContent=currentHistoryError.message;}
}
document.querySelector('#history-refresh').onclick=refreshGenerationHistory;
document.querySelector('#history-reset').onclick=async()=>{
 if(!confirm('이 생성기의 프롬프트·이력 목록을 초기화할까요? 실험 폴더의 입력과 결과 파일은 유지됩니다.'))return;
 try{const currentResetResponse=await fetch(historyRoutePrefix+'/history/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'reset'})});const currentResetPayload=await currentResetResponse.json();if(!currentResetResponse.ok)throw Error(currentResetPayload.error);await refreshGenerationHistory();}catch(currentResetError){historyStatusElement.textContent=currentResetError.message;}
};
refreshGenerationHistory();
setInterval(refreshGenerationHistory,10000);
