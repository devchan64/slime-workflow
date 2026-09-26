(()=>{
 if(window.top!==window||document.getElementById('management-gpu-status'))return;
 const status=document.createElement('div');status.id='management-gpu-status';status.setAttribute('role','status');status.className='input-hint';status.style.cssText='min-width:0;font-size:12px;overflow-wrap:anywhere;margin:0';
 const header=document.querySelector('header');const actions=document.querySelector('.manager-header-actions');if(header&&actions)header.insertBefore(status,actions);else (header||document.body).append(status);
 let lastText='';
 async function update(){
  try{const response=await fetch('/management/gpu-status',{cache:'no-store'});if(!response.ok)throw Error();const data=await response.json();const text=data.status==='busy'?'GPU 사용 중 · '+data.processes.map(item=>item.command+(item.id?' · '+item.id:' · PID '+item.pid)+(item.memory_mib!==null?' · '+item.memory_mib+' MiB':'')).join(' / '):data.status==='idle'?'GPU · 실행 중인 연산 작업 없음':'GPU · 상태 확인 불가';if(text!==lastText){status.textContent=text;lastText=text}}
  catch(error){status.textContent='GPU · 상태 조회 연결 실패';lastText=''}
  finally{setTimeout(update,3000)}
 }
 update();
})();
