import React,{useId} from 'react';

export default function LiveInstructionInput({text,busy,tooLong,onChange}){
  const helpId=useId(),errorId=useId();
  return <><label>실행 중 지시 <textarea aria-label="실행 중 지시" aria-invalid={tooLong || undefined} aria-describedby={[helpId,tooLong ? errorId : null].filter(Boolean).join(' ')} value={text} disabled={busy} onChange={event=>onChange(event.target.value)} placeholder="추가하거나 수정할 지시를 입력하세요"/></label>
    <small id={helpId}>지시는 8,000자까지 입력할 수 있습니다.</small>
    {tooLong && <p id={errorId} role="alert">지시는 8,000자까지 전달할 수 있습니다. 초과한 내용을 줄여 주세요.</p>}
  </>;
}
