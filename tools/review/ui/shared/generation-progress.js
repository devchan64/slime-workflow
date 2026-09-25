function resetGenerationProgress(){
 document.querySelector('#generation-progress').removeAttribute('value');
 document.querySelector('#generation-progress').style.accentColor='';
 document.querySelector('#progress-label').textContent='작업 시작 중';
 document.querySelector('#log').textContent='';document.querySelector('#log-file').hidden=true;
}
function renderGenerationProgress(currentJobRecord){
 const currentProgressRecord=currentJobRecord.progress;
 const currentStageLabels={starting:'시작 준비',imports:'환경 준비',load:'모델 로딩',adapters:'어댑터 로딩',inference:'이미지 생성',saving:'이미지 복원·저장',completed:'완료',failed:'실패',cancelled:'취소됨','waiting-gpu':'GPU 작업 대기','waiting-download':'다운로드 대기','download-model':'모델 다운로드','download-lightning':'Lightning 다운로드',generate:'생성 준비','cuda-check':'GPU 확인'};
 const currentProgressElement=document.querySelector('#generation-progress');
 document.querySelector('#cancel-generation').disabled=currentJobRecord.status!=='running';
 document.querySelector('#progress-label').textContent=(currentStageLabels[currentProgressRecord.stage]||currentProgressRecord.stage)+(currentProgressRecord.total?` · ${currentProgressRecord.step}/${currentProgressRecord.total} 스텝 · ${currentProgressRecord.percent}%`:'');
 if(currentJobRecord.status!=='running')currentProgressElement.value=currentProgressRecord.percent??0;
 else if(currentProgressRecord.percent===null)currentProgressElement.removeAttribute('value');else currentProgressElement.value=currentProgressRecord.percent;
 const currentLogElement=document.querySelector('#log');currentLogElement.textContent=currentJobRecord.log||'로그 출력 대기 중…';
 if(document.querySelector('#log-follow').checked)currentLogElement.scrollTop=currentLogElement.scrollHeight;
 const currentLogLink=document.querySelector('#log-file');currentLogLink.href=currentJobRecord.log_url;currentLogLink.hidden=!currentJobRecord.log_updated_at;
 document.querySelector('#log-updated').textContent=currentJobRecord.log_updated_at?'로그 최종 기록: '+new Date(currentJobRecord.log_updated_at*1000).toLocaleTimeString():'';
}
document.querySelector('#log-copy').onclick=async()=>{try{await navigator.clipboard.writeText(document.querySelector('#log').textContent);document.querySelector('#log-copy').textContent='복사 완료';}catch(currentCopyError){document.querySelector('#log-copy').textContent='복사 실패 · 직접 선택해 복사하세요';}};
document.querySelector('#cancel-generation').onclick=async()=>{
 const currentCancelButton=document.querySelector('#cancel-generation');currentCancelButton.disabled=true;
 try{const currentCancelRoute=document.querySelector('#generation-history').dataset.route;const currentCancelResponse=await fetch(currentCancelRoute+'/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:activeJobIdentifier})});const currentCancelRecord=await currentCancelResponse.json();if(!currentCancelResponse.ok)throw Error(currentCancelRecord.error);await synchronizeGenerationAvailability();document.querySelector('#status').textContent='취소됨';document.querySelector('#generation-progress').value=0;document.querySelector('#progress-label').textContent='취소됨';}catch(currentCancelError){document.querySelector('#status').textContent='취소 실패: '+currentCancelError.message;currentCancelButton.disabled=false;}
};
async function synchronizeGenerationAvailability(){
 const currentGeneratorRoute=document.querySelector('#generation-history').dataset.route;
 const currentActiveResponse=await fetch(currentGeneratorRoute+'/active');
 if(!currentActiveResponse.ok)throw Error('실행 상태를 확인하지 못했습니다.');
 const currentActiveRecord=await currentActiveResponse.json();
 document.querySelector('#submit').disabled=currentActiveRecord.running;
 const currentPrepareButton=document.querySelector('#prepare');if(currentPrepareButton)currentPrepareButton.disabled=currentActiveRecord.running;
 document.querySelector('#cancel-generation').disabled=!currentActiveRecord.running;
 if(!currentActiveRecord.running){
  activeJobIdentifier=null;
  sessionStorage.removeItem(currentGeneratorRoute.endsWith('2511')?'qwen2511Job':'qwen2512Job');
  document.querySelector('#status').textContent='입력 준비 완료 · 생성할 수 있습니다.';
 }else{
  activeJobIdentifier=currentActiveRecord.id;
  document.querySelector('#status').textContent='현재 작업이 실행 중입니다. 완료 또는 취소 후 생성할 수 있습니다.';
 }
}

document.querySelector('#randomize-seed').onclick=()=>{
 const generatedSeedValues=new Uint32Array(1);
 crypto.getRandomValues(generatedSeedValues);
 document.querySelector('#seed').value=String(generatedSeedValues[0]);
 document.querySelector('#seed').dispatchEvent(new Event('input',{bubbles:true}));
};
