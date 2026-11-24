export async function prepareFluxPreview({service,session,receiptScope,form,files,signal,verifyProposal,readReference,command,fetchPreview}){
  const check=()=>{if(signal.aborted)throw new DOMException('검토 중단','AbortError');};
  if(receiptScope)await verifyProposal((name,operation,payload)=>command(name,operation,payload,{signal}),receiptScope,receiptScope.proposal);
  check();
  if(files.length>2)throw new Error('참조 이미지는 두 장까지 선택하세요.');
  const {translation_source_ko,...input}=form;
  const payload={...input,width:Number(input.width),height:Number(input.height),seed:Number(input.seed),steps:Number(form.steps),images:await Promise.all(files.map(readReference)),action:'generate'};
  check();
  if(translation_source_ko.trim())payload.translation_source_ko=translation_source_ko.trim();
  const response=await fetchPreview(service,payload,signal);
  const result=await response.json();check();
  if(!response.ok)throw new Error(result?.detail || '입력을 확인하세요.');
  if(!result || typeof result.prompt!=='string' || (result.translation!=null && typeof result.translation!=='string'))throw new Error('입력 검토 응답을 확인할 수 없습니다.');
  let handoff=null;
  if(session){
    const owner=await command('hermes-agent','hermes-resident-status',{session_id:session},{signal});check();
    if(owner.session_id!==session || !owner.resident)throw new Error('대화 모델 상태를 확인할 수 없습니다.');
    if(owner.resident_id){
      if(owner.resident.state!=='ready')throw new Error('Qwen 3.8 상주 모델 상태를 확인한 뒤 다시 검토하세요.');
      handoff=await command('hermes-agent','hermes-gpu-handoff-preview',{session_id:session,resident_id:owner.resident_id,service,request:payload},{signal});check();
      if(handoff.session_id!==session || handoff.resident_id!==owner.resident_id || handoff.service!==service || !/^[a-f0-9]{64}$/.test(handoff.review_hash || ''))throw new Error('GPU 양도 검토 결과가 일치하지 않습니다.');
    }else if(owner.resident.state!=='not_found')throw new Error('대화 모델 상태를 확인할 수 없습니다.');
  }
  return {payload,result,handoff};
}
