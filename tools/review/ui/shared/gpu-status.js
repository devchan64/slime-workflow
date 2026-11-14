(()=>{
 if(window.top!==window||document.getElementById('management-gpu-status'))return;
 const status=document.createElement('div');status.id='management-gpu-status';status.setAttribute('role','status');status.className='input-hint';status.style.cssText='min-width:0;font-size:12px;overflow-wrap:anywhere;margin:0';
 const header=document.querySelector('header');const actions=document.querySelector('.manager-header-actions');if(header&&actions)header.insertBefore(status,actions);else (header||document.body).append(status);
 let lastText='';
 async function update(){
  try{const response=await fetch('/management/gpu-status',{cache:'no-store'});if(!response.ok)throw Error();const data=await response.json();let text=data.status==='busy'?'GPU 사용 중 · '+data.processes.map(item=>{const memory=['gtt','vram'].filter(domain=>Number.isInteger(item[domain+'_memory_mib'])).map(domain=>domain.toUpperCase()+' '+item[domain+'_memory_mib']+' MiB');return item.command+(item.id?' · '+item.id:' · PID '+item.pid)+(memory.length?' · '+memory.join(' · '):item.memory_mib!=null?' · '+item.memory_mib+' MiB':'')}).join(' / '):data.status==='idle'?'GPU · 실행 중인 연산 작업 없음':'GPU · 상태 확인 불가';for(const domain of ['gtt','vram']){const values=['used','free','total'].map(measure=>data[domain+'_'+measure+'_mib']);if(values.every(Number.isInteger))text+=' · '+domain.toUpperCase()+' 사용 '+values[0]+' · 여유 '+values[1]+' · 총 '+values[2]+' MiB'}if(text!==lastText){status.textContent=text;lastText=text}}
  catch(error){status.textContent='GPU · 상태 조회 연결 실패';lastText=''}
  finally{setTimeout(update,3000)}
 }
 update();
})();
