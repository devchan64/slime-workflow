// 저장형 도구가 공유하는 카드 선택·페이지 탐색 UI. 서버 명령은 호출자가 제공한다.
function renderSavedRecordHistory(containerElement,historyRecordItems,historyViewState,historyActionHandlers){
 const historyPageSize=8;
 const historyPageCount=Math.max(1,Math.ceil(historyRecordItems.length/historyPageSize));
 historyViewState.page=Math.min(historyViewState.page||0,historyPageCount-1);
 containerElement.classList.add('saved-record-history');
 containerElement.replaceChildren();
 const makeHistoryElement=(elementTagName,elementClassName,elementTextValue)=>{const createdHistoryElement=document.createElement(elementTagName);createdHistoryElement.className=elementClassName;createdHistoryElement.textContent=elementTextValue||'';return createdHistoryElement;};
 const historyToolbarElement=makeHistoryElement('div','generation-history-toolbar');
 historyToolbarElement.append(makeHistoryElement('span','',`총 ${historyRecordItems.length}건 · ${historyViewState.page+1} / ${historyPageCount}페이지`));
 for(const [buttonLabelValue,buttonDisabledValue,buttonActionHandler] of [['새로고침',false,historyActionHandlers.refresh],['← 이전',!historyViewState.page,()=>changeHistoryPage(-1)],['다음 →',historyViewState.page===historyPageCount-1,()=>changeHistoryPage(1)]]){const historyButtonElement=makeHistoryElement('button','',buttonLabelValue);historyButtonElement.disabled=buttonDisabledValue;historyButtonElement.onclick=buttonActionHandler;historyToolbarElement.append(historyButtonElement);}
 containerElement.append(historyToolbarElement);
 function changeHistoryPage(pageDeltaValue){historyViewState.page+=pageDeltaValue;historyViewState.selected=null;renderSavedRecordHistory(containerElement,historyRecordItems,historyViewState,historyActionHandlers);}
 const historyCardsElement=makeHistoryElement('div','generation-detail-cards');containerElement.append(historyCardsElement);
 for(const historyRecordValue of historyRecordItems.slice(historyViewState.page*historyPageSize,(historyViewState.page+1)*historyPageSize)){
  const historyCardElement=makeHistoryElement('button','generation-detail-card');historyCardElement.setAttribute('aria-pressed',String(historyViewState.selected===historyRecordValue.id));
  const historyHeadingElement=makeHistoryElement('span','history-card-heading');historyHeadingElement.append(makeHistoryElement('strong','',historyRecordValue.label||'좌표 저장'),makeHistoryElement('span','history-card-state','완료'));historyCardElement.append(historyHeadingElement,makeHistoryElement('time','',historyRecordValue.created_at.replace('T',' ').slice(0,19)));
  const historyFieldsElement=makeHistoryElement('dl','');const historyFrameField=makeHistoryElement('div','history-record-field');historyFrameField.append(makeHistoryElement('dt','','프레임'),makeHistoryElement('dd','',`${historyRecordValue.frames}개`));historyFieldsElement.append(historyFrameField);historyCardElement.append(historyFieldsElement,makeHistoryElement('span','history-card-id','ID · '+historyRecordValue.id),makeHistoryElement('span','history-card-select',historyViewState.selected===historyRecordValue.id?'선택됨':'이 작업 선택'));
  historyCardElement.onclick=()=>{historyViewState.selected=historyRecordValue.id;renderSavedRecordHistory(containerElement,historyRecordItems,historyViewState,historyActionHandlers);};historyCardsElement.append(historyCardElement);
  if(historyViewState.selected===historyRecordValue.id){const historyActionsElement=makeHistoryElement('div','generation-history-selected-actions');historyActionsElement.append(makeHistoryElement('p','history-action-caption','선택한 저장 이력'));const historyActionButtons=makeHistoryElement('div','saved-history-actions');historyActionsElement.append(historyActionButtons);for(const [actionLabelValue,actionCallbackValue] of [['입력값 조회',historyActionHandlers.inspect],['입력값 불러오기',historyActionHandlers.restore]]){const actionButtonElement=makeHistoryElement('button','',actionLabelValue);actionButtonElement.onclick=()=>actionCallbackValue(historyRecordValue);historyActionButtons.append(actionButtonElement);}historyCardsElement.append(historyActionsElement);}
 }
}
