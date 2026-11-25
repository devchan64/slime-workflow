import React,{useCallback,useEffect,useRef,useState} from 'react';
import {managementCommand,untilAborted} from './managementCommand.js';
import ReferenceImageInput from './ReferenceImageInput.jsx';
import SeedInput from './SeedInput.jsx';
import {referencePng} from './videoInputs.js';
import {formStateLabel} from './minimaxFormState.mjs';

const formError=(problem,fallback)=>problem?.name==='AbortError' ? '요청 시간이 초과됐습니다.' : problem instanceof TypeError ? '서버에 연결할 수 없습니다. 연결 상태를 확인하세요.' : (problem?.message || fallback);

export default function MiniMaxForms({session,initialFormId=''}) {
  const [rows,setRows]=useState(null),[selected,setSelected]=useState(null),[prompt,setPrompt]=useState('');
  const [seed,setSeed]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
  const [size,setSize]=useState('1024x1024'),[file,setFile]=useState(null),[checking,setChecking]=useState(false);
  const active=useRef(true), controller=useRef(null), operation=useRef(false);
  const listController=useRef(null),listEpoch=useRef(0),listBusy=useRef(false);
  const [listError,setListError]=useState('');
  const call=useCallback(async(command,payload)=>{
    const current=new AbortController();controller.current=current;
    const timeout=setTimeout(()=>current.abort(),30000);
    try{return await untilAborted(managementCommand('hermes-agent',command,payload,{signal:current.signal}),current.signal);}
    finally{clearTimeout(timeout);if(controller.current===current)controller.current=null;}
  },[]);
  useEffect(()=>{active.current=true;return()=>{active.current=false;controller.current?.abort();listController.current?.abort();};},[]);
  const refresh=useCallback(async()=>{
    if(operation.current || listBusy.current)return;
    listBusy.current=true;const epoch=listEpoch.current,current=new AbortController();listController.current=current;
    const timeout=setTimeout(()=>current.abort(),30000);
    try{const result=await untilAborted(managementCommand('hermes-agent','hermes-minimax-form-list',{session_id:session},{signal:current.signal}),current.signal);if(!Array.isArray(result?.forms))throw Error('폼 목록 형식 오류');if(active.current && epoch===listEpoch.current){setRows(result.forms);setListError('');}}
    catch(problem){if(active.current && epoch===listEpoch.current)setListError(formError(problem,'폼 목록을 확인할 수 없습니다.'));}
    finally{clearTimeout(timeout);if(listController.current===current)listController.current=null;listBusy.current=false;}
  },[session]);
  useEffect(()=>{refresh();},[refresh]);
  useEffect(()=>{const timer=setInterval(refresh,5000);return()=>clearInterval(timer);},[refresh]);
  async function open(form_id){
    if(operation.current)return;listEpoch.current++;operation.current=true;setBusy(true);setError('');setNotice('');
    try{const result=await call('hermes-minimax-form-read',{session_id:session,form_id});if(result?.session_id!==session || result?.form_id!==form_id || !Number.isInteger(result?.revision) || !result?.request || typeof result.request.prompt!=='string')throw Error('선택한 폼의 입력을 확인할 수 없습니다.');if(active.current){setSelected(result);setRows(old=>old?.map(row=>row.form_id===result.form_id ? {...row,revision:result.revision,state:result.state,receipt_state:result.receipt_state,job_id:result.job_id} : row) ?? old);setPrompt(result.request.prompt);setSeed(String(result.request.seed ?? ''));setSize(result.request.width+'x'+result.request.height);setFile(null);}}
    catch(problem){if(active.current)setError(formError(problem,'폼을 불러오지 못했습니다. 목록을 새로고침한 뒤 다시 열어 주세요.'));}
    finally{operation.current=false;if(active.current)setBusy(false);}
  }
  useEffect(()=>{if(initialFormId && /^[a-f0-9]{32}$/.test(initialFormId))open(initialFormId);},[initialFormId]);
  async function save(event){
    event.preventDefault();if(operation.current || !selected || selected.state!=='editing')return;
    if(rows?.some(row=>row.form_id===selected.form_id && (row.revision!==selected.revision || row.state!==selected.state))){setError('폼이 변경됐습니다. 최신 폼을 다시 열어 확인하세요.');return;}
    const number=Number(seed), max=selected.service==='minimax-h3-i2v'?2147483647:4294967295;
    if(checking || seed==='' || !prompt.trim() || !Number.isInteger(number) || number<0 || number>max){setError('프롬프트, 이미지 확인 상태와 시드를 확인하세요.');return;}
    listEpoch.current++;operation.current=true;setBusy(true);setError('');setNotice('');
    try{
      const request={...selected.request,prompt:prompt.trim(),seed:number};
      if(request.prompt!==selected.request.prompt)delete request.expected_prompt_sha256;
      if(selected.service==='minimax-h3-image'){
        const allowed=['512x512','1024x1024',selected.request.width+'x'+selected.request.height];
        if(!allowed.includes(size))throw Error('이미지 크기를 다시 확인하세요.');
        [request.width,request.height]=size.split('x').map(Number);
      }
      if(selected.service==='minimax-h3-i2v' && file){request.images=[await referencePng(file)];if(!active.current)return;}
      const result=await call('hermes-minimax-form-save',{session_id:session,form_id:selected.form_id,revision:selected.revision,request});
      if(result?.session_id!==session || result?.form_id!==selected.form_id || result?.revision!==selected.revision+1 || !result?.request)throw Error('저장 결과가 선택한 폼과 일치하지 않습니다.');
      if(active.current){setSelected(result);setPrompt(result.request.prompt);setSeed(String(result.request.seed ?? ''));setSize(result.request.width+'x'+result.request.height);setRows(old=>old?.map(row=>row.form_id===result.form_id ? {...row,revision:result.revision,state:result.state,job_id:result.job_id} : row) ?? old);setFile(null);setNotice('폼을 저장했습니다.');}
    }
    catch(problem){if(active.current)setError(formError(problem,'저장 결과를 확인할 수 없습니다.')+' 최신 폼을 다시 불러와 확인하세요.');}
    finally{operation.current=false;if(active.current)setBusy(false);}
  }
  const seedMax=selected?.service==='minimax-h3-i2v'?2147483647:4294967295;
  const invalidSeed=seed.trim()==='' || !Number.isInteger(Number(seed)) || Number(seed)<0 || Number(seed)>seedMax;
  const dirty=selected && (prompt!==selected.request.prompt || seed!==String(selected.request.seed ?? '') ||
    (selected.service==='minimax-h3-image' && size!==selected.request.width+'x'+selected.request.height) || !!file);
  const stale=selected && rows?.some(row=>row.form_id===selected.form_id && (row.revision!==selected.revision || row.state!==selected.state));
  return <section aria-label="MiniMax 접수폼"><h2>MiniMax 접수폼</h2><p>이 대화의 폼을 확인하고 수정합니다. 접수하려면 헤르메스에게 해당 폼을 대기열에 추가하도록 지시하세요.</p>
    <button type="button" disabled={busy} onClick={refresh}>목록 새로고침</button>{listError && <p role="status">폼 목록 갱신 실패 · 이전 조회 결과입니다. {listError}</p>}{error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {rows && (rows.length ? <ul>{rows.map(row=><li key={row.form_id}><button type="button" disabled={busy} onClick={()=>open(row.form_id)}>{row.service==='minimax-h3-image'?'이미지':'영상'} · {row.form_id.slice(0,8)} · v{row.revision} · {formStateLabel(row.state,row.receipt_state)}</button></li>)}</ul> : <p>이 대화에 저장된 MiniMax 접수폼이 없습니다.</p>)}
    {selected && <form onSubmit={save}><h3>{selected.service==='minimax-h3-image'?'이미지':'영상'} 접수폼 · v{selected.revision}</h3><p>상태: {formStateLabel(selected.state,selected.receipt_state)}{selected.job_id && ' · 작업 '+selected.job_id}</p>
      {dirty && <p role="status">저장하지 않은 수정 내용이 있습니다. 대화로 접수하기 전에 폼 수정 저장을 눌러 주세요.</p>}
      {stale && <p role="alert">다른 곳에서 폼이 변경됐습니다. 현재 입력을 확인한 뒤 목록에서 폼을 다시 열어 주세요.</p>}
      <fieldset disabled={busy || selected.state!=='editing'}><label>프롬프트<textarea required maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <SeedInput value={seed} max={seedMax} error={invalidSeed ? `0~${seedMax}의 정수를 입력하세요.` : ""} onChange={setSeed}/>
      {selected.service==='minimax-h3-image' ? <label>이미지 크기<select value={size} onChange={event=>setSize(event.target.value)}><option value="512x512">512×512</option><option value="1024x1024">1024×1024</option>{!['512x512','1024x1024'].includes(selected.request.width+'x'+selected.request.height) && <option value={selected.request.width+'x'+selected.request.height}>{selected.request.width}×{selected.request.height} · 저장된 설정</option>}</select></label> : <><ReferenceImageInput label="첫 프레임 이미지 변경" source={file} onCheckingChange={setChecking} onChange={setFile} disabled={busy}/><p>저장된 참조 이미지: {selected.request.images?.length ? '첨부됨' : '첨부 필요'}{file && ' · 새 이미지 선택됨'}</p></>}
      <p>설정: {selected.request.steps}스텝{selected.request.frames && ' · '+selected.request.frames+'프레임'}{selected.service==='minimax-h3-i2v' && ' · '+selected.request.width+'×'+selected.request.height}</p>
      <button type="submit" disabled={checking || stale}>{checking?'이미지 확인 중':'폼 수정 저장'}</button></fieldset>
      {selected.state!=='editing' && <p>현재 상태에서는 폼을 수정할 수 없습니다. 접수 상태를 확인해 주세요.</p>}</form>}
  </section>;
}
