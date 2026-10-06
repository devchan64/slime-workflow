/* 좌표·배율 변경은 전체 대상 검증 후 반환하며 입력 객체를 수정하지 않는다. */
function calculateJoypadTransforms(currentActionName,currentInputValues,currentTargetRecords){
 const currentAllowedActions=['read','up','down','left','right','scale-up','scale-down','set-x','set-y','set-scale','set-scaleX','set-scaleY','scaleX-up','scaleX-down','scaleY-up','scaleY-down'];
 if(!currentAllowedActions.includes(currentActionName))throw Error('지원하지 않는 조이패드 명령입니다.');
 if(!currentTargetRecords.length)throw Error('편집할 대상을 선택하세요.');
 if(currentActionName==='read')return currentTargetRecords.map(currentRecordValue=>({...currentRecordValue}));
 const currentMoveActions={up:['y',-1],down:['y',1],left:['x',-1],right:['x',1]};
 const currentIsMove=Object.hasOwn(currentMoveActions,currentActionName);
 const currentIsScale=/^(scale|scaleX|scaleY)-(up|down)$/.test(currentActionName);
 const currentStepValue=currentIsMove?currentInputValues.positionStep:currentInputValues.scaleStep;
 if((currentIsMove||currentIsScale)&&(typeof currentStepValue!=='number'||!Number.isFinite(currentStepValue)||currentStepValue<=0))throw Error('스텝은 0보다 큰 숫자여야 합니다.');
 return currentTargetRecords.map(currentRecordValue=>{
  const currentNextRecord={...currentRecordValue};
  let currentFieldName,currentFieldValue;
  if(currentIsMove){const [currentAxisName,currentDirectionSign]=currentMoveActions[currentActionName];currentFieldName=currentAxisName;currentFieldValue=currentRecordValue[currentAxisName]+currentDirectionSign*currentStepValue;}
  else if(currentIsScale){currentFieldName=currentActionName.split('-')[0];currentFieldValue=currentRecordValue[currentFieldName]+(currentActionName.endsWith('-up')?1:-1)*currentStepValue;}
  else{currentFieldName=currentActionName.slice(4);currentFieldValue=currentInputValues[currentFieldName];}
  if(typeof currentFieldValue!=='number'||!Number.isFinite(currentFieldValue))throw Error('적용할 수치를 입력하세요.');
  currentFieldValue=Math.round(currentFieldValue*1e10)/1e10;
  const currentMinimumValue=currentFieldName.startsWith('scale')?0.01:-8192,currentMaximumValue=currentFieldName.startsWith('scale')?8:8192;
  if(currentFieldValue<currentMinimumValue||currentFieldValue>currentMaximumValue)throw Error(`${currentFieldName} 허용 범위는 ${currentMinimumValue}~${currentMaximumValue}입니다.`);
  currentNextRecord[currentFieldName]=currentFieldValue;
  return currentNextRecord;
 });
}
if(typeof window!=='undefined')window.calculateJoypadTransforms=calculateJoypadTransforms;
if(typeof module!=='undefined')module.exports={calculateJoypadTransforms};
