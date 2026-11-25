import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseQuestionForm,formatQuestionAnswers,verifyQuestionTarget} from '../../gui/hermesQuestionForm.mjs';

const job='2026-11-25_22-30-44-0d6a944f';
const questions=[{title:'어떻게 진행할까요?',options:['승인','거절']}];
const block=value=>`HERMES_QUESTION_FORM\n${JSON.stringify(value)}\nEND_HERMES_QUESTION_FORM`;

test('valid question form preserves surrounding text and binds answers to the job',()=>{
  const parsed=parseQuestionForm('확인해 주세요.\n'+block({questions})+'\n추가 안내');
  assert.deepEqual(parsed.questions,questions);
  assert.match(parsed.display,/확인해 주세요/);
  assert.match(parsed.display,/추가 안내/);
  assert.match(formatQuestionAnswers(job,parsed.questions,['승인']),/질문 작업 2026-11-25_22-30-44-0d6a944f/);
  assert.match(formatQuestionAnswers(job,parsed.questions,['첫 줄\n둘째 줄']),/답변: 첫 줄\n답변 계속: 둘째 줄/);
  assert.ok(parseQuestionForm(block({questions})+'\nHERMES_IMAGE_PROPOSAL\n{}\nEND_HERMES_IMAGE_PROPOSAL'));
  assert.throws(()=>formatQuestionAnswers(job,questions,['  ']));
  assert.throws(()=>formatQuestionAnswers('bad',questions,['승인']));
});

test('invalid or ambiguous blocks do not become interactive forms',()=>{
  for(const value of [{questions:[]},{questions:[{title:'질문',options:['중복','중복']}]},{questions:[{title:'질문',options:['하나']}]},{questions:[{title:'질문\n추가',options:['예','아니요']}]},{questions,extra:true}])assert.equal(parseQuestionForm(block(value)),null);
  assert.equal(parseQuestionForm(block({questions})+'\n'+block({questions})),null);
  assert.equal(parseQuestionForm('HERMES_QUESTION_FORM\n{bad}\nEND_HERMES_QUESTION_FORM'),null);
});

test('a saved form target is carried into the answer and invalid targets are rejected',()=>{
  const target={type:'minimax-form',form_id:'a'.repeat(32),revision:3};
  const parsed=parseQuestionForm(block({questions,target}));
  assert.deepEqual(parsed.target,target);
  const answer=formatQuestionAnswers(job,parsed.questions,['승인'],parsed.target);
  assert.match(answer,/대상 폼 ID: a{32}/);
  assert.match(answer,/대상 폼 버전: 3/);
  for(const bad of [{...target,revision:0},{...target,revision:'3'},{...target,form_id:'bad'},{...target,type:'other'}])assert.equal(parseQuestionForm(block({questions,target:bad})),null);
  const handoff={...target,resident_id:'resident_123',review_hash:'b'.repeat(64)};
  const handoffForm=parseQuestionForm(block({questions,target:handoff}));
  assert.deepEqual(handoffForm.target,handoff);
  const consent=formatQuestionAnswers(job,questions,['GPU 양도에 동의'],handoff);
  assert.match(consent,/상주 모델 ID: resident_123/);
  assert.match(consent,/GPU 양도 검토: b{64}/);
  assert.equal(parseQuestionForm(block({questions,target:{...target,resident_id:'resident_123'}})),null);
});

test('a bound answer requires the same editable form in the current session',async()=>{
  const session='c'.repeat(32),target={type:'minimax-form',form_id:'a'.repeat(32),revision:3};
  const saved={session_id:session,form_id:target.form_id,revision:3,state:'editing',service:'minimax-h3-image',request:{prompt:'집',images:[]}};
  let requested;
  await verifyQuestionTarget(session,target,async payload=>(requested=payload,saved));
  assert.deepEqual(requested,{session_id:session,form_id:target.form_id});
  for(const change of [{revision:4},{state:'submitting'},{state:'external_receipt'},{session_id:'d'.repeat(32)},{form_id:'b'.repeat(32)}]){
    await assert.rejects(verifyQuestionTarget(session,target,async()=>({...saved,...change})),/변경되었거나/);
  }
  await assert.rejects(verifyQuestionTarget(session,target,async()=>{throw Error('조회 실패');}),/조회 실패/);
});
