import React,{useCallback,useEffect,useRef,useState} from 'react';
import {managementCommand,untilAborted} from './managementCommand.js';
import ReferenceImageInput from './ReferenceImageInput.jsx';
import SeedInput from './SeedInput.jsx';
import {referencePng} from './videoInputs.js';
import {formStateLabel} from './minimaxFormState.mjs';

const formError=(problem,fallback)=>problem?.name==='AbortError' ? '요청 시간이 초과됐습니다.' : problem instanceof TypeError ? '서버에 연결할 수 없습니다. 연결 상태를 확인하세요.' : (problem?.message || fallback);

function ImageFields({selected,size,setSize}){
  return <label>이미지 크기<select value={size} onChange={event=>setSize(event.target.value)}><option value="512x512">512×512</option><option value="1024x1024">1024×1024</option>{!['512x512','1024x1024'].includes(selected.request.width+'x'+selected.request.height) && <option value={selected.request.width+'x'+selected.request.height}>{selected.request.width}×{selected.request.height} · 저장된 설정</option>}</select></label>;
}

function VideoFields({selected,file,setFile,setChecking,busy}){
  return <><ReferenceImageInput label="첫 프레임 이미지 변경" source={file} onCheckingChange={setChecking} onChange={setFile} disabled={busy}/><p>저장된 참조 이미지: {selected.request.images?.length ? '첨부됨' : '첨부 필요'}{file && ' · 새 이미지 선택됨'}</p></>;
}

const editors={"minimax-h3-image":ImageFields,"minimax-h3-i2v":VideoFields};

export default function MiniMaxForms({session,initialFormId=''}) {
  const [selected,setSelected]=useState(null),[prompt,setPrompt]=useState('');
  const [seed,setSeed]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
  const [size,setSize]=useState('1024x1024'),[file,setFile]=useState(null),[checking,setChecking]=useState(false);
  const active=useRef(true), controller=useRef(null), operation=useRef(false);
  const call=useCallback(async(command,payload)=>{
    const current=new AbortController();controller.current=current;
    const timeout=setTimeout(()=>current.abort(),30000);
    try{return await untilAborted(managementCommand('hermes-agent',command,payload,{signal:current.signal}),current.signal);}
    finally{clearTimeout(timeout);if(controller.current===current)controller.current=null;}
  },[]);
  useEffect(()=>{active.current=true;return()=>{active.current=false;controller.current?.abort();};},[]);
  async function open(form_id){
    if(operation.current)return;operation.current=true;setBusy(true);setError('');setNotice('');
    try{const result=await call('hermes-minimax-form-read',{session_id:session,form_id});if(result?.session_id!==session || result?.form_id!==form_id || !Number.isInteger(result?.revision) || !result?.request || typeof result.request.prompt!=='string')throw Error('선택한 폼의 입력을 확인할 수 없습니다.');if(active.current){setSelected(result);setPrompt(result.request.prompt);setSeed(String(result.request.seed ?? ''));setSize(result.request.width+'x'+result.request.height);setFile(null);}}
    catch(problem){if(active.current)setError(formError(problem,'폼을 불러오지 못했습니다. 다시 조회하세요.'));}
    finally{operation.current=false;if(active.current)setBusy(false);}
  }
  useEffect(()=>{if(initialFormId && /^[a-f0-9]{32}$/.test(initialFormId))open(initialFormId);},[initialFormId]);
  async function save(event){
    event.preventDefault();if(operation.current || !selected || selected.state!=='editing')return;
    const number=Number(seed), max=selected.service==='minimax-h3-i2v'?2147483647:4294967295;
    if(checking || seed==='' || !prompt.trim() || !Number.isInteger(number) || number<0 || number>max){setError('프롬프트, 이미지 확인 상태와 시드를 확인하세요.');return;}
    operation.current=true;setBusy(true);setError('');setNotice('');
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
      if(active.current){setSelected(result);setPrompt(result.request.prompt);setSeed(String(result.request.seed ?? ''));setSize(result.request.width+'x'+result.request.height);setFile(null);setNotice('폼을 저장했습니다.');}
    }
    catch(problem){if(active.current)setError(formError(problem,'저장 결과를 확인할 수 없습니다.')+' 최신 폼을 다시 불러와 확인하세요.');}
    finally{operation.current=false;if(active.current)setBusy(false);}
  }
  const seedMax=selected?.service==='minimax-h3-i2v'?2147483647:4294967295;
  const invalidSeed=seed.trim()==='' || !Number.isInteger(Number(seed)) || Number(seed)<0 || Number(seed)>seedMax;
  const dirty=selected && (prompt!==selected.request.prompt || seed!==String(selected.request.seed ?? '') ||
    (selected.service==='minimax-h3-image' && size!==selected.request.width+'x'+selected.request.height) || !!file);
  const Fields=selected && Object.hasOwn(editors,selected.service) && editors[selected.service];
  return <section aria-label="저장된 접수폼">
    <p>폼 ID · <code>{initialFormId}</code></p>
    {busy && !selected && <p role="status">접수폼 조회 중…</p>}
    {error && <div role="alert">{error} <button type="button" disabled={busy} onClick={()=>open(initialFormId)}>다시 조회</button></div>}
    {notice && <p role="status">{notice}</p>}
    {selected && !Fields && <p role="alert">지원되지 않는 생성기입니다. {selected.service}</p>}
    {Fields && <form onSubmit={save}><h3>{selected.service==='minimax-h3-image'?'이미지':'영상'} 접수폼 · v{selected.revision}</h3><p>상태: {formStateLabel(selected.state,selected.receipt_state)}{selected.job_id && ' · 작업 '+selected.job_id}</p>
      {dirty && <p role="status">저장하지 않은 수정 내용이 있습니다. 대화로 접수하기 전에 폼 수정 저장을 눌러 주세요.</p>}
      <fieldset disabled={busy || selected.state!=='editing'}><label>프롬프트<textarea required maxLength={8000} value={prompt} onChange={event=>setPrompt(event.target.value)}/></label>
      <SeedInput value={seed} max={seedMax} error={invalidSeed ? `0~${seedMax}의 정수를 입력하세요.` : ""} onChange={setSeed}/>
      <Fields {...{selected,size,setSize,file,setFile,setChecking,busy}}/>
      <p>설정: {selected.request.steps}스텝{selected.request.frames && ' · '+selected.request.frames+'프레임'}{selected.service==='minimax-h3-i2v' && ' · '+selected.request.width+'×'+selected.request.height}</p>
      <button type="submit" disabled={checking}>{checking?'이미지 확인 중':'폼 수정 저장'}</button></fieldset>
      {selected.state!=='editing' && <p>현재 상태에서는 폼을 수정할 수 없습니다. 접수 상태를 확인해 주세요.</p>}</form>}
  </section>;
}
