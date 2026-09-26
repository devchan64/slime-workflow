// 타일 전용 입력만 추가하고 실행·취소·로그·이력은 공용 이미지 클라이언트를 사용한다.
let tileConfigurationRecord=null;
const tileTypeSelector=document.querySelector('#tile-type');
const tileUserPrompt=document.querySelector('#prompt');
const tileSubmitButton=document.querySelector('#submit');
const tileGenerationStatus=document.querySelector('#status');
const countTileWords=promptTextValue=>promptTextValue.trim()?promptTextValue.trim().split(/\s+/).length:0;
function updateTilePromptDisplay(){
 if(!tileConfigurationRecord)return;
 const selectedTileRecord=tileConfigurationRecord.types[tileTypeSelector.value];
 document.querySelector('#tile-base-prompt').textContent=selectedTileRecord.base_prompt;
 document.querySelector('#tile-style-prompt').textContent=tileConfigurationRecord.style_prompt;
 const baseWordCount=countTileWords(selectedTileRecord.base_prompt),styleWordCount=countTileWords(tileConfigurationRecord.style_prompt),userWordCount=countTileWords(tileUserPrompt.value);
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
  const referenceFileValue=document.querySelector('#tile-reference-'+referenceSlotIndex).files[0];if(!referenceFileValue)continue;
  if(referenceFileValue.size>3000000)throw Error('참조 PNG는 장당 3MB 이하입니다.');
  const referenceDataUrl=await new Promise((resolveReferenceRead,rejectReferenceRead)=>{const referenceFileReader=new FileReader();referenceFileReader.onload=()=>resolveReferenceRead(referenceFileReader.result);referenceFileReader.onerror=()=>rejectReferenceRead(Error('참조 읽기 실패'));referenceFileReader.readAsDataURL(referenceFileValue);});
  referenceImageValues.push(referenceDataUrl.split(',')[1]);
 }
 }catch(referenceReadError){tileGenerationStatus.textContent=referenceReadError.message;return;}
 startGenerationJob({images:referenceImageValues,action:'generate' ,tile_type:tileTypeSelector.value,user_prompt:tileUserPrompt.value,seed:Number(document.querySelector('#seed').value),steps:Number(document.querySelector('#steps').value),width:Number(document.querySelector('#resolution').value.split('x')[0]),height:Number(document.querySelector('#resolution').value.split('x')[1])});
};
const tileEstimateElement=document.createElement('p');tileEstimateElement.className='input-hint';tileEstimateElement.setAttribute('role','status');tileEstimateElement.textContent='예상 시간 · 생성 시작 후 같은 설정의 완료 이력으로 계산합니다.';document.querySelector('.progress-panel').append(tileEstimateElement);
const sharedProgressRenderer=renderGenerationProgress;
renderGenerationProgress=currentJobRecord=>{sharedProgressRenderer(currentJobRecord);const remainingSecondsValue=currentJobRecord.estimate?.remaining_seconds;tileEstimateElement.textContent=currentJobRecord.status!=='running'?'예상 시간 · 작업 종료':remainingSecondsValue>0?'예상 남은 시간 약 '+Math.ceil(remainingSecondsValue/60)+'분 · 완료 예상 '+new Date(Date.now()+remainingSecondsValue*1000).toLocaleString('ko-KR')+' · 같은 스텝·크기의 완료 이력 기준 (GPU 대기 시 지연 가능)':'예상 시간 계산 중 · 비교할 이력이 없거나 기존 시간을 초과했습니다.';};
fetch('/tile-map-generator/catalog').then(async responseValue=>{if(!responseValue.ok)throw Error('타일 설정 조회 실패');tileConfigurationRecord=await responseValue.json();updateTilePromptDisplay();await synchronizeGenerationAvailability();}).catch(errorValue=>{tileGenerationStatus.textContent=errorValue.message;tileSubmitButton.disabled=true;});

for(let referenceSlotIndex=1;referenceSlotIndex<=3;referenceSlotIndex++){
 const referenceInputElement=document.querySelector('#tile-reference-'+referenceSlotIndex),referencePreviewElement=document.querySelector('#tile-reference-preview-'+referenceSlotIndex);
 referenceInputElement.onchange=()=>{if(referencePreviewElement.dataset.objectUrl)URL.revokeObjectURL(referencePreviewElement.dataset.objectUrl);const referenceFileValue=referenceInputElement.files[0];referencePreviewElement.hidden=!referenceFileValue;if(referenceFileValue){referencePreviewElement.dataset.objectUrl=URL.createObjectURL(referenceFileValue);referencePreviewElement.src=referencePreviewElement.dataset.objectUrl;}};
 document.querySelector('[data-clear-reference="'+referenceSlotIndex+'"]').onclick=()=>{referenceInputElement.value='';referenceInputElement.onchange();};
}
