// 타일 전용 입력만 추가하고 실행·취소·로그·이력은 공용 이미지 클라이언트를 사용한다.
let tileConfigurationRecord=null;
const tileTypeSelector=document.querySelector('#tile-type');
const tileUserPrompt=document.querySelector('#prompt');
const tileSubmitButton=document.querySelector('#submit');
const tileGenerationStatus=document.querySelector('#status');
const tileReferenceFileRecords=new Map();
let selectedReferenceSlotIndex=1;
const countTileWords=promptTextValue=>promptTextValue.trim()?promptTextValue.trim().split(/\s+/).length:0;
function updateTilePromptDisplay(){
 if(!tileConfigurationRecord)return;
 const selectedTileRecord=tileConfigurationRecord.types[tileTypeSelector.value];
 document.querySelector('#tile-base-prompt').textContent=selectedTileRecord.base_prompt;
 document.querySelector('#tile-style-prompt').textContent=tileConfigurationRecord.style_prompt;
 const baseWordCount=document.querySelector('#tile-use-base').checked?countTileWords(selectedTileRecord.base_prompt):0,styleWordCount=document.querySelector('#tile-use-style').checked?countTileWords(tileConfigurationRecord.style_prompt):0,userWordCount=countTileWords(tileUserPrompt.value);
 document.querySelector('#base-word-count').textContent=baseWordCount+'단어';document.querySelector('#style-word-count').textContent=styleWordCount+'단어';
 document.querySelector('#tile-word-count').textContent='사용자 '+userWordCount+'단어 · 최종 '+(baseWordCount+styleWordCount+userWordCount)+'단어 / 100단어 미만';
 tileUserPrompt.setCustomValidity(baseWordCount+styleWordCount+userWordCount>=100?'최종 프롬프트를 100단어 미만으로 줄이세요.':'');
}
for(const resolutionOptionValue of [...document.querySelector('#resolution').options]){const [widthValue,heightValue]=resolutionOptionValue.value.split('x');if(widthValue!==heightValue)resolutionOptionValue.remove();}
document.querySelector('#resolution').value='512x512';
tileTypeSelector.onchange=updateTilePromptDisplay;tileUserPrompt.addEventListener('input',updateTilePromptDisplay);
tileSubmitButton.textContent='타일 생성';tileSubmitButton.disabled=true;tileSubmitButton.setAttribute('aria-describedby','tile-word-count');
document.querySelector('#generate').onsubmit=async eventValue=>{
 eventValue.preventDefault();if(!tileConfigurationRecord){tileGenerationStatus.textContent='고정 프롬프트를 불러오는 중입니다.';return;}
 updateTilePromptDisplay();if(!tileUserPrompt.reportValidity())return;
 const referenceImageValues=[];
 try{
 for(let referenceSlotIndex=1;referenceSlotIndex<=3;referenceSlotIndex++){
  const referenceFileValue=tileReferenceFileRecords.get(referenceSlotIndex);if(!referenceFileValue)continue;
  if(referenceFileValue.size>3000000)throw Error('참조 PNG는 장당 3MB 이하입니다.');
  const referenceDataUrl=await new Promise((resolveReferenceRead,rejectReferenceRead)=>{const referenceFileReader=new FileReader();referenceFileReader.onload=()=>resolveReferenceRead(referenceFileReader.result);referenceFileReader.onerror=()=>rejectReferenceRead(Error('참조 읽기 실패'));referenceFileReader.readAsDataURL(referenceFileValue);});
  referenceImageValues.push(referenceDataUrl.split(',')[1]);
 }
 }catch(referenceReadError){tileGenerationStatus.textContent=referenceReadError.message;return;}
 startGenerationJob({use_base_prompt:document.querySelector('#tile-use-base').checked,use_style_prompt:document.querySelector('#tile-use-style').checked,images:referenceImageValues,action:'generate' ,tile_type:tileTypeSelector.value,user_prompt:tileUserPrompt.value,seed:Number(document.querySelector('#seed').value),steps:Number(document.querySelector('#steps').value),width:Number(document.querySelector('#resolution').value.split('x')[0]),height:Number(document.querySelector('#resolution').value.split('x')[1])});
};
const tileEstimateElement=document.createElement('p');tileEstimateElement.className='input-hint';tileEstimateElement.setAttribute('role','status');tileEstimateElement.textContent='예상 시간 · 생성 시작 후 같은 설정의 완료 이력으로 계산합니다.';document.querySelector('.progress-panel').append(tileEstimateElement);
const sharedProgressRenderer=renderGenerationProgress;
renderGenerationProgress=currentJobRecord=>{sharedProgressRenderer(currentJobRecord);const remainingSecondsValue=currentJobRecord.estimate?.remaining_seconds;tileEstimateElement.textContent=currentJobRecord.status!=='running'?'예상 시간 · 작업 종료':remainingSecondsValue>0?'예상 남은 시간 약 '+Math.ceil(remainingSecondsValue/60)+'분 · 완료 예상 '+new Date(Date.now()+remainingSecondsValue*1000).toLocaleString('ko-KR')+' · 같은 스텝·크기의 완료 이력 기준 (GPU 대기 시 지연 가능)':'예상 시간 계산 중 · 비교할 이력이 없거나 기존 시간을 초과했습니다.';};
fetch('/tile-map-generator/catalog').then(async responseValue=>{if(!responseValue.ok)throw Error('타일 설정 조회 실패');tileConfigurationRecord=await responseValue.json();updateTilePromptDisplay();await synchronizeGenerationAvailability();}).catch(errorValue=>{tileGenerationStatus.textContent=errorValue.message;tileSubmitButton.disabled=true;});

function setTileReferenceFile(referenceSlotIndex,referenceFileValue){
 const referenceInputElement=document.querySelector('#tile-reference-'+referenceSlotIndex),referencePreviewElement=document.querySelector('#tile-reference-preview-'+referenceSlotIndex);
 if(referenceFileValue&&referenceFileValue.type!=='image/png'){tileGenerationStatus.textContent='참조 이미지는 PNG만 사용할 수 있습니다.';return;}
 if(referenceFileValue&&referenceFileValue.size>3000000){tileGenerationStatus.textContent='참조 PNG는 장당 3MB 이하입니다.';return;}
 if(referencePreviewElement.dataset.objectUrl)URL.revokeObjectURL(referencePreviewElement.dataset.objectUrl);
 if(referenceFileValue){tileReferenceFileRecords.set(referenceSlotIndex,referenceFileValue);referencePreviewElement.dataset.objectUrl=URL.createObjectURL(referenceFileValue);referencePreviewElement.src=referencePreviewElement.dataset.objectUrl;referencePreviewElement.hidden=false;}else{tileReferenceFileRecords.delete(referenceSlotIndex);referencePreviewElement.removeAttribute('src');referencePreviewElement.hidden=true;}
 referenceInputElement.value='';selectTileReferenceSlot(referenceSlotIndex);
 tileGenerationStatus.textContent='이미지 '+referenceSlotIndex+(referenceFileValue?' 추가 완료':' 제거 완료');
}
function selectTileReferenceSlot(referenceSlotIndex){
 selectedReferenceSlotIndex=referenceSlotIndex;
 for(let currentSlotIndex=1;currentSlotIndex<=3;currentSlotIndex++){
  const currentSlotElement=document.querySelector('[data-reference-slot="'+currentSlotIndex+'"]'),isSelectedSlot=currentSlotIndex===referenceSlotIndex;
  currentSlotElement.classList.toggle('is-selected',isSelectedSlot);currentSlotElement.setAttribute('aria-pressed',String(isSelectedSlot));
 }
}
for(let referenceSlotIndex=1;referenceSlotIndex<=3;referenceSlotIndex++){
 const referenceInputElement=document.querySelector('#tile-reference-'+referenceSlotIndex),referenceSlotElement=document.querySelector('[data-reference-slot="'+referenceSlotIndex+'"]');
 referenceSlotElement.onclick=()=>{selectTileReferenceSlot(referenceSlotIndex);referenceSlotElement.focus({preventScroll:true});};
 referenceSlotElement.addEventListener('focusin',()=>selectTileReferenceSlot(referenceSlotIndex));
 referenceSlotElement.addEventListener('dragover',referenceDragEvent=>{referenceDragEvent.preventDefault();referenceDragEvent.dataTransfer.dropEffect='copy';});
 referenceSlotElement.addEventListener('drop',referenceDropEvent=>{
  referenceDropEvent.preventDefault();referenceDropEvent.stopPropagation();selectTileReferenceSlot(referenceSlotIndex);referenceSlotElement.focus({preventScroll:true});
  const droppedReferenceFiles=Array.from(referenceDropEvent.dataTransfer?.files||[]);
  if(droppedReferenceFiles.length!==1){tileGenerationStatus.textContent='한 칸에 PNG 이미지 한 장을 놓으세요.';return;}
  setTileReferenceFile(referenceSlotIndex,droppedReferenceFiles[0]);
 });
 referenceSlotElement.onfocus=()=>selectTileReferenceSlot(referenceSlotIndex);
 referenceSlotElement.onkeydown=keyboardEventValue=>{if(keyboardEventValue.key==='Enter'||keyboardEventValue.key===' '){keyboardEventValue.preventDefault();selectTileReferenceSlot(referenceSlotIndex);}};
 referenceInputElement.onchange=()=>setTileReferenceFile(referenceSlotIndex,referenceInputElement.files[0]);
 document.querySelector('[data-select-reference="'+referenceSlotIndex+'"]').onclick=()=>{selectTileReferenceSlot(referenceSlotIndex);referenceInputElement.click();};
 document.querySelector('[data-clear-reference="'+referenceSlotIndex+'"]').onclick=()=>setTileReferenceFile(referenceSlotIndex,null);
}
selectTileReferenceSlot(selectedReferenceSlotIndex);
document.addEventListener('paste',pasteEventValue=>{
 const clipboardImageFile=Array.from(pasteEventValue.clipboardData?.items||[]).map(currentClipboardItem=>currentClipboardItem.kind==='file'?currentClipboardItem.getAsFile():null).find(currentFileValue=>currentFileValue?.type.startsWith('image/'));
 if(!clipboardImageFile)return;
 pasteEventValue.preventDefault();setTileReferenceFile(selectedReferenceSlotIndex,clipboardImageFile);
});

document.addEventListener('generation-history-reset',resetEventValue=>{
 if(resetEventValue.detail.route!=='/tile-map-generator')return;
 activeJobIdentifier=null;sessionStorage.removeItem('tileMapJob');
 const previousResultImage=document.querySelector('#result');previousResultImage.hidden=true;previousResultImage.removeAttribute('src');
 document.querySelector('#download').hidden=true;resetGenerationProgress();setBusyState(false);
 tileGenerationStatus.textContent='타일 생성 이력과 결과 파일을 삭제했습니다.';
});

for(const promptToggleId of ['tile-use-base','tile-use-style'])document.getElementById(promptToggleId).onchange=updateTilePromptDisplay;

// 입력 순서: 타일 종류 → 참조 → 프롬프트 → 생성 설정 → 실행.
const tileSettingsRow=document.querySelector('#generate .settings-row');
const tilePromptLabel=document.querySelector('label[for="prompt"]');
const tileReferenceGroup=document.querySelector('.reference-input-group');
const tileTypeLabel=document.querySelector('label[for="tile-type"]');
const tileGenerateForm=document.querySelector('#generate');
tileGenerateForm.prepend(tileTypeLabel,tileTypeSelector,tileReferenceGroup);
const tileToggleGroup=document.createElement('div');tileToggleGroup.className='prompt-toggle-row';
for(const toggleElementId of ['tile-use-base','tile-use-style'])tileToggleGroup.append(document.getElementById(toggleElementId).closest('label'));
tilePromptLabel.before(tileToggleGroup);
if(tileSettingsRow)document.querySelector('#generate .generation-actions').before(tileSettingsRow);
