'use strict';
const animationDirectionLabels={down_left:'전방 좌측',down_right:'전방 우측',up_left:'후방 좌측',up_right:'후방 우측'};
const animationElementLookup=elementIdentifier=>document.getElementById(elementIdentifier);
const animationLogController=ManagementLogViewer.attach(animationElementLookup('execution-log'),animationElementLookup('execution-log-text'));
let cancellationRequestPending=false;
let lastSelectedMotionIdentifier=null;
let generationSubmissionPending=false,generationAvailabilityChecked=false,activeGenerationProgress=null;
let animationCatalogRecord=null,activeGenerationIdentifier=null,playbackResultRecord=null,playbackJobIdentifier=null,currentFramePosition=0,animationPlaybackTimer=null,playbackRequestCounter=0;
async function executeAnimationCommand(commandOperationName,commandPayloadValue={}){
 const commandResponseValue=await fetch('/management/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({service:'character-animation',command:commandOperationName,payload:commandPayloadValue})});
 const commandResponseRecord=await commandResponseValue.json();if(!commandResponseValue.ok)throw Error(commandResponseRecord.error);return commandResponseRecord;
}
function readAnimationSelection(){return {motion:animationElementLookup('motion-choice').value,character:animationElementLookup('character-choice').value,source:animationElementLookup('source-choice').value,steps:Number(animationElementLookup('generation-steps').value),frame_step:Number(animationElementLookup('generation-frame-step').value),directions:Array.from(document.querySelectorAll('[name=animation-direction]:checked')).map(directionCheckboxElement=>directionCheckboxElement.value)};}
function refreshAnimationSelection(){
 if(!animationCatalogRecord)return;
 const selectedAnimationValues=readAnimationSelection(),selectedMotionRecord=animationCatalogRecord.motions.find(motionRecordValue=>motionRecordValue.id===selectedAnimationValues.motion);
 if(lastSelectedMotionIdentifier!==selectedMotionRecord.id){animationElementLookup('generation-frame-step').value=selectedMotionRecord.frame_step;selectedAnimationValues.frame_step=selectedMotionRecord.frame_step;lastSelectedMotionIdentifier=selectedMotionRecord.id;}
 const selectedFrameCount=Math.ceil(selectedMotionRecord.frames/selectedAnimationValues.frame_step);
 animationElementLookup('auxiliary-prompt').textContent=selectedAnimationValues.directions.map(directionNameValue=>animationDirectionLabels[directionNameValue]+'\n'+animationCatalogRecord.direction_prompts[directionNameValue].auxiliary).join('\n\n')||'생성할 방향을 선택하세요.';
 window.selectMotionAssetPreview(selectedMotionRecord);
 animationElementLookup('frame-count').textContent=`원본 ${selectedMotionRecord.frames}프레임 · ${selectedAnimationValues.frame_step}프레임 간격 → ${selectedFrameCount}프레임 × ${selectedAnimationValues.directions.length}방향 = ${selectedFrameCount*selectedAnimationValues.directions.length}장 · ${selectedMotionRecord.fps} FPS 재생 시 방향당 ${selectedFrameCount/selectedMotionRecord.fps}초`;
 const previewDirectionName=selectedAnimationValues.directions[0]||'down_left';
 for(const referenceRoleName of ['character']){const previewImageElement=animationElementLookup(referenceRoleName+'-preview'),previewImagePath=`/character-animation/reference/${selectedAnimationValues.motion}/${selectedAnimationValues.character}/${selectedAnimationValues.source}/${previewDirectionName}/${referenceRoleName}`;if(previewImageElement.getAttribute('src')!==previewImagePath)previewImageElement.src=previewImagePath;}
 refreshGenerationAvailability();
}
function refreshGenerationAvailability(){
 const generationSubmitButton=animationElementLookup('submit'),availabilityMessageElement=animationElementLookup('generation-availability');
 const selectedDirectionCount=document.querySelectorAll('[name=animation-direction]:checked').length;
 generationSubmitButton.disabled=!animationCatalogRecord||!generationAvailabilityChecked||generationSubmissionPending||Boolean(activeGenerationIdentifier)||!selectedDirectionCount;
 generationSubmitButton.textContent=generationSubmissionPending?'생성 시작 중…':activeGenerationIdentifier?'생성 진행 중':'애니메이션 생성';
 animationElementLookup('show-active-generation').hidden=!activeGenerationIdentifier;
 if(generationSubmissionPending)availabilityMessageElement.textContent='생성 요청을 접수하고 있습니다.';
 else if(!animationCatalogRecord||!generationAvailabilityChecked)availabilityMessageElement.textContent='서버의 생성 가능 여부를 확인하는 중입니다.';
 else if(activeGenerationIdentifier)availabilityMessageElement.textContent=`실행 중: ${activeGenerationIdentifier}${activeGenerationProgress?` · ${activeGenerationProgress.completed}/${activeGenerationProgress.total}프레임 완료`:''}. 완료 또는 취소 후 새로 생성할 수 있습니다.`;
 else availabilityMessageElement.textContent=selectedDirectionCount?'생성할 수 있습니다.':'생성할 방향을 하나 이상 선택하세요.';
}
animationElementLookup('show-active-generation').onclick=()=>{animationElementLookup('execution-log').open=true;animationElementLookup('status').scrollIntoView({behavior:'smooth',block:'center'});};
function stopAnimationPlayback(){clearInterval(animationPlaybackTimer);animationPlaybackTimer=null;}
function renderAnimationFrame(){
 if(!playbackResultRecord)return;
 const currentDirectionFrames=playbackResultRecord.frames[animationElementLookup('playback-direction').value];
 currentFramePosition=(currentFramePosition+currentDirectionFrames.length)%currentDirectionFrames.length;
 animationElementLookup('output-frame').src=`/character-animation/files/${playbackJobIdentifier}/${currentDirectionFrames[currentFramePosition]}`;
 animationElementLookup('frame-position').value=currentFramePosition;
 animationElementLookup('frame-label').textContent=`${currentFramePosition+1} / ${currentDirectionFrames.length}장${playbackResultRecord.source_frame_numbers?.[animationElementLookup('playback-direction').value]?` · 원본 ${playbackResultRecord.source_frame_numbers[animationElementLookup('playback-direction').value][currentFramePosition]}번`:''} · ${animationElementLookup('result-playback-fps').value} FPS · ${(currentDirectionFrames.length/Number(animationElementLookup('result-playback-fps').value)).toLocaleString('ko-KR',{maximumFractionDigits:2})}초/회`;
}
function selectPlaybackDirection(){
 stopAnimationPlayback();currentFramePosition=0;
 animationElementLookup('frame-position').max=playbackResultRecord.frames[animationElementLookup('playback-direction').value].length-1;renderAnimationFrame();
}
window.playGenerationRecord=async historyRecordValue=>{
 const currentPlaybackRequest=++playbackRequestCounter;
 stopAnimationPlayback();
 try{
  const generationStatusRecord=await executeAnimationCommand('status',{id:historyRecordValue.id});
  if(currentPlaybackRequest!==playbackRequestCounter)return;
  if(generationStatusRecord.status!=='completed'||!generationStatusRecord.result)throw Error('완료된 결과가 필요합니다.');
  playbackJobIdentifier=historyRecordValue.id;playbackResultRecord=generationStatusRecord.result;
  animationElementLookup('playback-direction').replaceChildren(...Object.keys(playbackResultRecord.frames).map(directionNameValue=>new Option(animationDirectionLabels[directionNameValue],directionNameValue)));
  animationElementLookup('result-title').textContent=`${playbackJobIdentifier} · ${generationStatusRecord.request.motion} · ${generationStatusRecord.request.character} · ${generationStatusRecord.request.source} · ${(generationStatusRecord.request.steps||4)===4?'4스텝 Lightning':'30스텝'}`;
  for(const elementIdentifier of ['playback-direction','frame-previous','frame-play','frame-stop','frame-next','frame-position'])animationElementLookup(elementIdentifier).disabled=false;
  animationElementLookup('output-frame').hidden=false;animationElementLookup('playback-empty').hidden=true;selectPlaybackDirection();
  animationElementLookup('result-title').scrollIntoView({behavior:'smooth',block:'center'});
 }catch(playbackErrorValue){animationElementLookup('status').textContent=playbackErrorValue.message;}
};
animationElementLookup('playback-direction').onchange=selectPlaybackDirection;
animationElementLookup('frame-play').onclick=()=>{if(!playbackResultRecord)return;stopAnimationPlayback();animationPlaybackTimer=setInterval(()=>{currentFramePosition++;renderAnimationFrame();},1000/Number(animationElementLookup('result-playback-fps').value));};
animationElementLookup('frame-stop').onclick=stopAnimationPlayback;
for(const [elementIdentifier,frameIncrementValue] of [['frame-previous',-1],['frame-next',1]])animationElementLookup(elementIdentifier).onclick=()=>{stopAnimationPlayback();currentFramePosition+=frameIncrementValue;renderAnimationFrame();};
animationElementLookup('frame-position').oninput=()=>{stopAnimationPlayback();currentFramePosition=Number(animationElementLookup('frame-position').value);renderAnimationFrame();};
animationElementLookup('animation-form').onchange=refreshAnimationSelection;
animationElementLookup('select-all').onclick=()=>{document.querySelectorAll('[name=animation-direction]').forEach(directionCheckboxElement=>directionCheckboxElement.checked=true);refreshAnimationSelection();};
animationElementLookup('animation-form').onsubmit=async submissionEventValue=>{
 submissionEventValue.preventDefault();if(generationSubmissionPending||activeGenerationIdentifier)return;generationSubmissionPending=true;refreshGenerationAvailability();
 try{const generationStartRecord=await executeAnimationCommand('generate',readAnimationSelection());activeGenerationIdentifier=generationStartRecord.id;activeGenerationProgress=null;cancellationRequestPending=false;animationElementLookup('status').textContent='생성을 시작했습니다.';animationElementLookup('cancel-generation').disabled=false;await refreshGenerationHistory();}
 catch(generationErrorValue){animationElementLookup('status').textContent=generationErrorValue.message;}
 finally{generationSubmissionPending=false;refreshGenerationAvailability();}
};
animationElementLookup('cancel-generation').onclick=async()=>{
 if(!activeGenerationIdentifier)return;animationElementLookup('cancel-generation').disabled=true;
 try{cancellationRequestPending=true;await executeAnimationCommand('cancel',{id:activeGenerationIdentifier});animationElementLookup('status').textContent='취소 요청 중…';}catch(cancelErrorValue){cancellationRequestPending=false;animationElementLookup('status').textContent=cancelErrorValue.message;}
};
function renderGenerationStatus(generationStatusRecord){
 const progressRecordValue=generationStatusRecord.progress,requestRecordValue=generationStatusRecord.request;
 const stageLabelValues={preparing:'생성 준비 중',load:'모델 불러오는 중',inference:'이미지 생성 중',saving:'결과 저장 중','waiting-gpu':'GPU 작업 대기 중',completed:'생성 완료',failed:'생성 실패',cancelled:'생성 취소됨'};
 const isRunningValue=generationStatusRecord.status==='running';
 const currentStageValue=isRunningValue?progressRecordValue?.stage:generationStatusRecord.status;
 animationElementLookup('status').textContent=cancellationRequestPending&&isRunningValue?'취소 요청 처리 중':stageLabelValues[currentStageValue]||'진행 상황 확인 중';
 if(requestRecordValue){
  const motionLabelText=animationCatalogRecord.motions.find(motionRecordValue=>motionRecordValue.id===requestRecordValue.motion)?.label||requestRecordValue.motion;
  const perDirectionCount=requestRecordValue.frames_per_direction;
  animationElementLookup('job-summary').textContent=`접수된 작업 · ${motionLabelText} · ${requestRecordValue.source==='anny'?'ANNY':'OpenPose'} · ${requestRecordValue.steps===30?'30스텝 표준':'4스텝 Lightning'} · ${requestRecordValue.frame_step||1}프레임 간격 · ${requestRecordValue.directions.length}방향${perDirectionCount?` × 방향당 ${perDirectionCount}장`:''}`;
 }
 const completedCountValue=progressRecordValue?.completed,totalCountValue=progressRecordValue?.total;
 const hasValidCounts=Number.isInteger(completedCountValue)&&Number.isInteger(totalCountValue)&&totalCountValue>0&&completedCountValue>=0&&completedCountValue<=totalCountValue;
 const percentageValue=hasValidCounts?Math.floor(1000*completedCountValue/totalCountValue)/10:null;
 animationElementLookup('completed-image-count').textContent=hasValidCounts?`${completedCountValue} / ${totalCountValue}장`:'확인 중';
 animationElementLookup('completed-image-percent').textContent=percentageValue===null?'—':`${percentageValue}%`;
 if(percentageValue===null)animationElementLookup('generation-progress').removeAttribute('value');else animationElementLookup('generation-progress').value=percentageValue;
 animationElementLookup('current-image-position').textContent=isRunningValue&&progressRecordValue?.direction?`${animationDirectionLabels[progressRecordValue.direction]} · ${progressRecordValue.direction_index}/${progressRecordValue.direction_total}번째 (원본 ${progressRecordValue.frame}번)`:'—';
 animationElementLookup('current-inference-step').textContent=isRunningValue&&Number.isInteger(progressRecordValue?.inference_completed)?`${progressRecordValue.inference_completed} / ${progressRecordValue.inference_steps}스텝`:isRunningValue?'스텝 시작 전':'—';
 animationElementLookup('generation-stage-note').textContent=generationStatusRecord.error|| (isRunningValue?'전체 진행률은 저장 완료된 이미지 기준입니다. 추론 스텝은 현재 이미지 한 장의 진행 상황입니다.':generationStatusRecord.status==='completed'?'모든 이미지 저장을 마쳤습니다. 아래에서 결과를 재생할 수 있습니다.':'작업이 종료되었습니다. 완료 수는 종료 시점까지 저장한 이미지 수입니다. 로그에서 상세 내용을 확인하세요.');
 animationElementLookup('job-location').textContent=`ID: ${generationStatusRecord.id||activeGenerationIdentifier}\n저장 경로: ${generationStatusRecord.path}`;
 animationLogController.update(generationStatusRecord.log);
 animationElementLookup('cancel-generation').disabled=!isRunningValue||cancellationRequestPending;
}
async function pollAnimationGeneration(){
 try{
  if(!animationCatalogRecord)return;
  if(!activeGenerationIdentifier&&!generationSubmissionPending){const activeGenerationRecord=await executeAnimationCommand('active');if(activeGenerationRecord.running)activeGenerationIdentifier=activeGenerationRecord.id;generationAvailabilityChecked=true;}
  if(activeGenerationIdentifier){
   const generationStatusRecord=await executeAnimationCommand('status',{id:activeGenerationIdentifier});
   const generationProgressRecord=generationStatusRecord.progress;activeGenerationProgress=generationProgressRecord;
   renderGenerationStatus(generationStatusRecord);
   if(generationStatusRecord.status!=='running'){
    const completedGenerationIdentifier=activeGenerationIdentifier;activeGenerationIdentifier=null;activeGenerationProgress=null;cancellationRequestPending=false;
    if(generationStatusRecord.status==='completed')await window.playGenerationRecord({id:completedGenerationIdentifier});
    await refreshGenerationHistory();
   }
   refreshAnimationSelection();
  }
  refreshGenerationAvailability();
 }catch(pollErrorValue){animationElementLookup('status').textContent='상태 조회 오류: '+pollErrorValue.message;}
 finally{setTimeout(pollAnimationGeneration,1500);}
}
(async()=>{
 try{
  animationCatalogRecord=await executeAnimationCommand('catalog');
  for(const [catalogCollectionName,elementIdentifier] of [['motions','motion-choice'],['characters','character-choice']])animationElementLookup(elementIdentifier).replaceChildren(...animationCatalogRecord[catalogCollectionName].map(catalogOptionRecord=>new Option(catalogOptionRecord.label,catalogOptionRecord.id)));
  for(const directionNameValue of animationCatalogRecord.directions){const directionLabelElement=document.createElement('label'),directionCheckboxElement=document.createElement('input');directionCheckboxElement.type='checkbox';directionCheckboxElement.name='animation-direction';directionCheckboxElement.value=directionNameValue;directionCheckboxElement.checked=true;directionLabelElement.append(directionCheckboxElement,animationDirectionLabels[directionNameValue]);animationElementLookup('direction-options').append(directionLabelElement);}
  animationElementLookup('base-prompt').textContent=animationCatalogRecord.prompts.base;animationElementLookup('auxiliary-prompt').textContent=animationCatalogRecord.prompts.auxiliary;
  animationElementLookup('status').textContent='대기 중 · 모션과 생성할 방향을 선택하세요.';refreshAnimationSelection();
 }catch(catalogErrorValue){animationElementLookup('status').textContent=catalogErrorValue.message;}
 pollAnimationGeneration();
})();

animationElementLookup('result-playback-fps').onchange=()=>{if(!playbackResultRecord)return;const wasPlaybackRunning=animationPlaybackTimer!==null;renderAnimationFrame();if(wasPlaybackRunning)animationElementLookup('frame-play').click();};
