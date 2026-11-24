import React,{useState} from 'react';
import {managementCommand} from './managementCommand.js';

function PendingItem({item,index,session,refresh}){
  const key=`hermes-queue-edit:${session}:${item.request_id}`;
  const [draft,setDraft]=useState(()=>{try{return JSON.parse(sessionStorage.getItem(key)) || null;}catch{return null;}});
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const owned=Boolean(draft?.token && item.edit_token===draft.token);
  function remember(value){setDraft(value);if(value)sessionStorage.setItem(key,JSON.stringify(value));else sessionStorage.removeItem(key);}
  async function send(action){
    if(busy)return;setBusy(true);setError('');
    try{
      let current=draft;
      if(action==='begin' && !current){current={token:crypto.randomUUID().replaceAll('-',''),text:item.prompt};remember(current);}
      if(!current?.token)throw new Error('편집 소유권을 확인할 수 없습니다.');
      await managementCommand('hermes-agent','hermes-chat-queue-edit',{session_id:session,request_id:item.request_id,revision:item.revision,action,token:current.token,...(action==='save'?{prompt:current.text}:{})});
      if(action!=='begin')remember(null);
      refresh();
    }catch(problem){setError((problem.message || '편집 상태를 확인할 수 없습니다.')+' · 상태를 다시 확인하세요.');refresh();}
    finally{setBusy(false);}
  }
  return <article className="message user conversation-pending-message">
    <b>나 · {item.edit_token?'수정 중 · 전송 보류':item.state==='dispatching'?'실행 준비 중':`대기 중 · ${index+1}번째`}</b>
    {owned ? <><textarea aria-label="대기 지시 수정" value={draft.text} onChange={event=>remember({...draft,text:event.target.value})}/><div><button type="button" disabled={busy || !draft.text.trim() || draft.text.length>12000} onClick={()=>send('save')}>수정 저장 후 대기</button><button type="button" disabled={busy} onClick={()=>send('cancel')}>수정 취소</button></div></> : <><p>{item.prompt}</p>{item.state==='queued' && !item.edit_token && <button type="button" disabled={busy} onClick={()=>send('begin')}>대기 지시 수정</button>}{item.edit_token && <small>다른 화면에서 수정 중입니다.</small>}</>}
    {error && <p role="alert">{error}</p>}
  </article>;
}
export function ConversationPending({items,session,refresh}) {
  const pending=Array.isArray(items) ? items.filter(item=>item && ['queued','dispatching'].includes(item.state) && typeof item.prompt==='string') : [];
  if(!pending.length)return null;
  return <section aria-label="대화 대기 요청" className="conversation-pending">{pending.map((item,index)=><PendingItem key={item.request_id} {...{item,index,session,refresh}}/>)}</section>;
}
