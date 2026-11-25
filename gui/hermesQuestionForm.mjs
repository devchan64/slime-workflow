const BLOCK=/\n?^HERMES_QUESTION_FORM[ \t]*\n([\s\S]*?)\nEND_HERMES_QUESTION_FORM[ \t]*(?=\n|$)/gm;
const label=value=>typeof value==='string' && value.trim()===value && value.length>0 && value.length<=300 && !/[\r\n\u0000-\u001f]/.test(value);

export function parseQuestionForm(answer){
  if(typeof answer!=='string' || answer.length>50000)return null;
  const matches=[...answer.matchAll(BLOCK)];
  if(matches.length!==1 || answer.split('HERMES_QUESTION_FORM').length!==3)return null;
  let data;
  try{data=JSON.parse(matches[0][1]);}catch{return null;}
  if(!data || Array.isArray(data) || Object.keys(data).some(key=>!['questions','target'].includes(key)) || !Array.isArray(data.questions) || data.questions.length<1 || data.questions.length>3)return null;
  if(data.target!==undefined){
    const target=data.target,keys=target && !Array.isArray(target) ? Object.keys(target).sort().join(',') : '';
    if(!['form_id,revision,type','form_id,resident_id,review_hash,revision,type'].includes(keys) || target.type!=='minimax-form' || !/^[a-f0-9]{32}$/.test(target.form_id) || !Number.isSafeInteger(target.revision) || target.revision<1)return null;
    if(target.resident_id!==undefined && (!/^[A-Za-z0-9_-]{8,80}$/.test(target.resident_id) || !/^[a-f0-9]{64}$/.test(target.review_hash)))return null;
  }
  for(const question of data.questions){
    if(!question || Array.isArray(question) || Object.keys(question).sort().join(',')!=='options,title' || !label(question.title) || !Array.isArray(question.options) || question.options.length<2 || question.options.length>5 || !question.options.every(label) || new Set(question.options).size!==question.options.length)return null;
  }
  if(new Set(data.questions.map(question=>question.title)).size!==data.questions.length)return null;
  return {questions:data.questions,target:data.target || null,display:answer.slice(0,matches[0].index)+answer.slice(matches[0].index+matches[0][0].length)};
}

export function formatQuestionAnswers(job,questions,answers,target=null){
  if(!/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job) || !Array.isArray(answers) || answers.length!==questions.length || answers.some(answer=>typeof answer!=='string' || !answer.trim() || answer.length>4000))throw new Error('모든 질문에 답변해 주세요.');
  const binding=target ? `대상 폼 ID: ${target.form_id}\n대상 폼 버전: ${target.revision}\n`+(target.resident_id ? `상주 모델 ID: ${target.resident_id}\nGPU 양도 검토: ${target.review_hash}\n` : '') : '';
  const text=`질문 작업 ${job}에 대한 답변:\n`+binding+questions.map((q,i)=>`${i+1}. ${q.title}\n`+answers[i].trim().replace(/\r\n?/g,'\n').split('\n').map((line,n)=>(n?'답변 계속: ':'답변: ')+line).join('\n')).join('\n');
  if(text.length>7500)throw new Error('답변을 합쳐 7,500자 이내로 작성해 주세요.');
  return text;
}

export async function verifyQuestionTarget(session,target,read){
  const form=await read({session_id:session,form_id:target.form_id});
  if(form?.session_id!==session || form?.form_id!==target.form_id || form?.revision!==target.revision || form?.state!=='editing')throw Error('질문한 폼이 변경되었거나 접수가 시작되었습니다. 최신 폼을 확인하세요.');
  if(!['minimax-h3-image','minimax-h3-i2v'].includes(form.service) || !form.request || typeof form.request.prompt!=='string' || !Array.isArray(form.request.images))throw Error('질문한 폼의 입력을 확인할 수 없습니다.');
  return form;
}
