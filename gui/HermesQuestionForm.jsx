import React,{useEffect,useId,useRef,useState} from 'react';
import {formatQuestionAnswers,verifyQuestionTarget} from './hermesQuestionForm.mjs';
import {managementCommand,untilAborted} from './managementCommand.js';

export default function HermesQuestionForm({job,session,questions,target,onDraft}){
  const statusId=useId();
  const [choices,setChoices]=useState(()=>questions.map(()=>''));
  const [custom,setCustom]=useState(()=>questions.map(()=>''));
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [targetState,setTargetState]=useState({status:target?'loading':'none'}),[targetRevision,retryTarget]=useState(0);
  const lock=useRef(false),active=useRef(true),request=useRef(null);
  useEffect(()=>{active.current=true;return()=>{active.current=false;request.current?.abort();};},[]);
  useEffect(()=>{
    if(!target){setTargetState({status:'none'});return;}
    let mounted=true;const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
    setTargetState({status:'loading'});
    verifyQuestionTarget(session,target,payload=>untilAborted(managementCommand('hermes-agent','hermes-minimax-form-read',payload,{signal:controller.signal}),controller.signal))
      .then(form=>{if(mounted)setTargetState({status:'ready',form});})
      .catch(problem=>{if(mounted)setTargetState({status:'error',message:problem?.name==='AbortError' ? '폼 확인 시간이 초과됐습니다.' : problem?.message || '폼을 확인할 수 없습니다.'});})
      .finally(()=>clearTimeout(timer));
    return()=>{mounted=false;clearTimeout(timer);controller.abort();};
  },[session,target?.form_id,target?.revision,targetRevision]);
  function choose(index,value){setChoices(previous=>previous.map((item,i)=>i===index ? value : item));setError('');}
  async function prepare(event){
    event.preventDefault();
    if(lock.current || (target && targetState.status!=='ready'))return;
    lock.current=true;setBusy(true);
    try{
      const answer=formatQuestionAnswers(job,questions,choices.map((value,i)=>value==='custom' ? custom[i] : value.startsWith('option:') ? questions[i].options[Number(value.slice(7))] : ''),target);
      if(target){
        const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);request.current=controller;
        try{await verifyQuestionTarget(session,target,payload=>untilAborted(managementCommand('hermes-agent','hermes-minimax-form-read',payload,{signal:controller.signal}),controller.signal));}
        finally{clearTimeout(timer);if(request.current===controller)request.current=null;}
        if(!active.current)return;
      }
      if(active.current){onDraft(answer);setError('');}
    }
    catch(problem){if(active.current)setError(problem?.name==='AbortError' ? '폼 확인 시간이 초과됐습니다. 다시 시도해 주세요.' : problem?.message || '답변을 확인해 주세요.');}
    finally{lock.current=false;if(active.current)setBusy(false);}
  }
  return <form className="hermes-question-form" aria-label="헤르메스 질문 폼" onSubmit={prepare}>
    {target && <section aria-label="질문 대상 폼"><p>대상 폼 ID: <code>{target.form_id}</code> · 버전 {target.revision}</p>
      {target.resident_id && <p>GPU 양도에 동의하면 이 대화의 Qwen 상주 모델을 해제하고 이미지를 생성한 뒤 다시 적재합니다. 양도 검토 ID: <code>{target.review_hash}</code></p>}
      {targetState.status==='loading' && !busy && <p id={statusId} role="status">대상 폼을 확인하고 있습니다.</p>}
      {targetState.status==='error' && <><p id={!busy?statusId:undefined} role="alert">{targetState.message} 다시 확인해 주세요.</p><button type="button" onClick={()=>retryTarget(value=>value+1)}>다시 확인</button></>}
      {targetState.status==='ready' && <><p>{targetState.form.service} · {targetState.form.request.width}×{targetState.form.request.height} · 시드 {targetState.form.request.seed} · 참조 {targetState.form.request.images.length}장</p><p>{targetState.form.request.prompt}</p>{targetState.form.request.images.length===0 && /참조(?:한|할|되는)?\s*(?:이미지|사진|그림)|reference\s+image/i.test(targetState.form.request.prompt) && <p role="status">프롬프트에 참조 이미지가 언급되어 있지만 첨부된 이미지가 없습니다. 필요한 참조를 접수폼에 첨부하고 저장해 주세요.</p>}</>}
    </section>}
    {busy && <p id={statusId} role="status">답변 작성을 위해 대상 폼을 다시 확인하고 있습니다.</p>}
    {questions.map((question,index)=><fieldset key={index} disabled={busy} aria-describedby={busy?statusId:undefined}><legend>{question.title}</legend>
      {question.options.map((option,optionIndex)=><label key={optionIndex}><input type="radio" name={`${job}-${index}`} checked={choices[index]===`option:${optionIndex}`} onChange={()=>choose(index,`option:${optionIndex}`)}/>{option}</label>)}
      <label><input type="radio" name={`${job}-${index}`} checked={choices[index]==='custom'} onChange={()=>choose(index,'custom')}/>직접 입력</label>
      {choices[index]==='custom' && <textarea aria-label={`${question.title} 직접 입력`} maxLength={4000} value={custom[index]} onChange={event=>setCustom(previous=>previous.map((value,i)=>i===index ? event.target.value : value))}/>}
    </fieldset>)}
    {error && <p role="alert">{error}</p>}
    <p>답변을 메시지에 작성합니다. 확인 후 보내기를 눌러 주세요.</p><button type="submit" disabled={busy || (target && targetState.status!=='ready')} aria-describedby={busy || (target && targetState.status!=='ready')?statusId:undefined}>{busy?'폼 확인 중':'답변 작성'}</button>
  </form>;
}
