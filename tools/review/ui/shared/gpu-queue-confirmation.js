// GPU 사용 또는 대기 작업이 있을 때만 새 GPU 작업 접수를 확인한다.
async function confirmGpuQueueStart() {
 const queueResponseValue=await fetch('/management/gpu-queue',{cache:'no-store'});
 if(!queueResponseValue.ok)throw new Error('GPU 대기열을 확인하지 못했습니다. 잠시 후 다시 시도하세요.');
 const queueRecordValue=await queueResponseValue.json();
 const pendingJobValues=Array.isArray(queueRecordValue.jobs)?queueRecordValue.jobs:[];
 const activeGpuProcessValues=queueRecordValue.gpu_status?.status==='busy'&&Array.isArray(queueRecordValue.gpu_status.processes)?queueRecordValue.gpu_status.processes:[];
 if(!pendingJobValues.length&&!activeGpuProcessValues.length)return true;
 return await new Promise(resolveConfirmation=>{
  const dialogElementValue=document.createElement('dialog');
  dialogElementValue.className='management-gpu-queue-confirmation';
  dialogElementValue.setAttribute('aria-labelledby','gpu-queue-confirmation-title');
  dialogElementValue.setAttribute('aria-modal','true');
  dialogElementValue.style.cssText='max-width:520px;width:calc(100% - 40px);padding:24px;border:1px solid #52647c;border-radius:12px;background:#182333;color:#edf3fa;box-sizing:border-box';
  dialogElementValue.innerHTML='<h2 id="gpu-queue-confirmation-title" style="margin:0 0 12px">GPU 작업 대기열에 추가할까요?</h2><p>GPU가 사용 중이거나 대기 작업이 있습니다. 추가하면 앞선 작업 이후 순서대로 실행됩니다.</p><ul style="max-height:200px;overflow:auto;padding-left:20px"></ul><p style="display:flex;justify-content:flex-end;gap:12px;margin:20px 0 0"><button type="button" data-answer="no">추가하지 않기</button><button type="button" data-answer="yes">대기열에 추가</button></p>';
  const pendingListElement=dialogElementValue.querySelector('ul');
  for(const activeProcessRecord of activeGpuProcessValues){const activeItemElement=document.createElement('li');activeItemElement.textContent='GPU 사용 중 · '+(activeProcessRecord.command||'알 수 없는 GPU 작업')+(activeProcessRecord.id?' · '+activeProcessRecord.id:'');pendingListElement.append(activeItemElement);}
  for(const pendingJobRecord of pendingJobValues){const pendingItemElement=document.createElement('li');const serviceLabelValue=({'momask':'MoMask 모션 생성','character-animation':'캐릭터 애니메이션','tile-map':'타일맵 생성','image':'이미지 생성','anny':'ANNY 렌더'}[pendingJobRecord.service]||pendingJobRecord.service||'알 수 없는 작업');pendingItemElement.textContent='대기 중 · '+serviceLabelValue+(pendingJobRecord.id?' · '+pendingJobRecord.id:'');pendingListElement.append(pendingItemElement);}
  for(const dialogButtonElement of dialogElementValue.querySelectorAll('button'))dialogButtonElement.style.cssText='padding:9px 14px;border-radius:6px;border:1px solid #788da8;background:#263952;color:#fff;cursor:pointer';
  const finishConfirmationValue=confirmedValue=>{dialogElementValue.close();dialogElementValue.remove();resolveConfirmation(confirmedValue);};
  dialogElementValue.addEventListener('cancel',eventValue=>{eventValue.preventDefault();finishConfirmationValue(false);});
  dialogElementValue.querySelector('[data-answer="no"]').onclick=()=>finishConfirmationValue(false);
  dialogElementValue.querySelector('[data-answer="yes"]').onclick=()=>finishConfirmationValue(true);
  document.body.append(dialogElementValue);dialogElementValue.showModal();dialogElementValue.querySelector('[data-answer="no"]').focus();
 });
}
