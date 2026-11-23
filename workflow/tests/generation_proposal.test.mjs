import test from 'node:test';
import assert from 'node:assert/strict';
import {readGenerationProposal,audioProposalInputs,generationProposalScope,vaceProposalInputs,funProposalInputs,wan21ProposalInputs,writerProposalId} from '../../gui/generationProposal.mjs';
test('audio, video and writer proposals are read only from their current session',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64);
  for(const [kind,proposal] of Object.entries({audio:{service:'sfx-dasheng-audiogen',request:{prompt:'water',seed:42}},video:{service:'wan22-vace',mode:'text',prompt:'walk'},writer:{mode:'write',prompt:'story'}})){
    const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_'+kind.toUpperCase()+'_PROPOSAL'}}]},calls=[];
    const command=async(_service,name)=>{calls.push(name);return name==='hermes-session-view'?page:{job_id:job,proposal};};
    assert.deepEqual(await readGenerationProposal(command,{session,job,snapshot,offset:0,kind}),proposal);
    assert.deepEqual(calls,['hermes-session-view','hermes-'+kind+'-proposal']);
    page.messages[0].session_job_unique=false;
    await assert.rejects(readGenerationProposal(command,{session,job,snapshot,offset:0,kind}),/확인할 수 없습니다/);
  }
});
test('proposal lookup times out during session or proposal retrieval',async(t)=>{
  t.mock.timers.enable({apis:['setTimeout']});
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64);
  const scope={session,job,snapshot,offset:0,kind:'video'};
  const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_VIDEO_PROPOSAL'}}]};
  for(const blocked of ['hermes-session-view','hermes-video-proposal']){
    const calls=[];
    const command=async(_service,name,_payload,{signal})=>{
      calls.push(name);
      if(name===blocked)return new Promise((_,reject)=>signal.addEventListener('abort',()=>reject(new Error('aborted')),{once:true}));
      return page;
    };
    const result=readGenerationProposal(command,scope);
    await Promise.resolve();
    t.mock.timers.tick(30000);
    await assert.rejects(result,/대화 제안 조회 시간이 초과/);
    assert.equal(calls.at(-1),blocked);
  }
});
test('VACE proposal transfers only mode and prompt after validating the target',()=>{
  const defaults={mode:'text',prompt:'',steps:16},proposal={service:'wan22-vace',mode:'pose',prompt:'walking',steps:2};
  assert.deepEqual(vaceProposalInputs(defaults,proposal),{mode:'pose',prompt:'walking',steps:16});
  assert.throws(()=>vaceProposalInputs(defaults,{...proposal,service:'dwpose'}),/확인/);
  assert.throws(()=>vaceProposalInputs(defaults,{...proposal,mode:'unsupported'}),/확인/);
  assert.deepEqual(generationProposalScope('?proposal_job=job&proposal_snapshot=hash&proposal_offset=6','session','video'),{session:'session',job:'job',snapshot:'hash',offset:6,kind:'video'});
  assert.throws(()=>generationProposalScope('?proposal_job=job&proposal_offset=bad','session','video'),/이력/);
});
test('audio proposal fills only the matching generator inputs',()=>{
  const defaults={prompt:'',seed:1,loop_request:false,other:'default'};
  const proposal={service:'sfx-dasheng-audiogen',request:{action:'generate',prompt:'water',seed:42,loop_request:true,other:'ignored'}};
  assert.deepEqual(audioProposalInputs(defaults,proposal,proposal.service),{prompt:'water',seed:42,loop_request:true,other:'default'});
  assert.throws(()=>audioProposalInputs(defaults,proposal,'music-heartmula'),/다릅니다/);
  assert.throws(()=>audioProposalInputs(defaults,{...proposal,request:{action:'prepare'}},proposal.service),/다릅니다/);
});
test('Wan Fun accepts only the video input supported by the current form',()=>{
  const defaults={prompt:'',images:[],pose_video:'',frames:21};
  const proposal={service:'wan22-fun-control',mode:'pose_video',prompt:'walking',frames:99};
  assert.deepEqual(funProposalInputs(defaults,proposal),{...defaults,prompt:'walking'});
  for(const mode of ['frames','driving_video'])assert.throws(()=>funProposalInputs(defaults,{...proposal,mode}),/포즈 영상/);
  assert.throws(()=>funProposalInputs(defaults,{...proposal,service:'dwpose'}),/포즈 영상/);
});
test('Wan 2.1 proposals transfer only prompts to the matching generator',()=>{
  const defaults={prompt:'',steps:4,images:[]};
  for(const [service,mode] of [['wan21-t2v','text'],['wan21-i2v','first_frame']]){
    const proposal={service,mode,prompt:'a boss fight',steps:99,images:['ignored']};
    assert.deepEqual(wan21ProposalInputs(defaults,proposal,service),{...defaults,prompt:'a boss fight'});
    assert.throws(()=>wan21ProposalInputs(defaults,{...proposal,mode:mode==='text'?'first_frame':'text'},service));
    assert.throws(()=>wan21ProposalInputs(defaults,{...proposal,prompt:' '},service));
    assert.throws(()=>wan21ProposalInputs(defaults,proposal,service==='wan21-t2v'?'wan21-i2v':'wan21-t2v'));
  }
});
test('writer proposal uses a stable session and job receipt across tabs',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678';
  const id=await writerProposalId(session,job);
  assert.match(id,/^writer_[a-f0-9]{64}$/);
  assert.equal(id,await writerProposalId(session,job));
  assert.notEqual(id,await writerProposalId('b'.repeat(32),job));
  await assert.rejects(writerProposalId(session,'invalid'));
});
