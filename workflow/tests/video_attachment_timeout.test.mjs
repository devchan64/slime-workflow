import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('VACE와 Fun Control은 영상 정보 지연 시 기존 입력을 유지한다',async()=>{
 for(const screen of ['VacePage','FunControlPage'])for(const stalled of ['fetch','json']){
  const source=readFileSync(new URL(`../../gui/${screen}.jsx`,import.meta.url),'utf8');
  const code=screen==='VacePage' ? source.slice(source.indexOf('  async function inspectVideo('),source.indexOf('  const attachments=')) : source.slice(source.indexOf('  async function attach('),source.indexOf('  async function load('));
  let timer,files={pose_video:'기존'},errors={},checking={},busy=false;
  const never=new Promise(()=>{}),fetcher=()=>stalled==='fetch'?never:Promise.resolve({ok:true,json:()=>never});
  const context=vm.createContext({AbortController,untilAborted,fetch:fetcher,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},
   videoSequences:{current:{}},videoControllers:{current:{}},attachmentProcessing:{current:false},attachmentRevision:{current:0},attachmentEpoch:{current:0},poseInspection:{current:null},
   videoData:async()=> '새 입력',referencePng:async()=>'',setFiles:fn=>files=fn(files),setVideoInfo:()=>{},setRequest:fn=>files=fn(files),
   setFileErrors:fn=>errors=fn(errors),setChecking:fn=>checking=fn(checking),setBusy:value=>busy=value,setError:value=>errors.message=value,
   setPoseError:value=>errors.pose_video=value,requestErrorMessage:problem=>problem.message});
  vm.runInContext(code,context);const file={type:'video/mp4',size:10};
  const pending=screen==='VacePage'?context.selectVideo('pose_video',file):context.attach(file,'pose_video');
  await new Promise(resolve=>setImmediate(resolve));timer();await pending;
  assert.equal(files.pose_video,'기존');assert.match(errors.pose_video,/시간.*초과/);
  assert.equal(screen==='VacePage'?checking.pose_video:busy,false);
  context.fetch=async()=>({ok:true,json:async()=>({maximum_frames:81,summary:'확인됨'})});
  await (screen==='VacePage'?context.selectVideo('pose_video',file):context.attach(file,'pose_video'));
  assert.equal(files.pose_video,screen==='VacePage'?file:'새 입력');assert.equal(errors.pose_video,'');
  assert.equal(screen==='VacePage'?checking.pose_video:busy,false);
 }
});

test('VACE는 손상된 영상 정보 응답으로 기존 입력을 바꾸지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/VacePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function inspectVideo('),source.indexOf('  const attachments='));
 for(const response of [{maximum_frames:0,summary:'잘못된 길이'},{maximum_frames:21,summary:{bad:true}},null]){
  let files={pose_video:'기존'},errors={},checking={};
  const context=vm.createContext({AbortController,untilAborted,fetch:async()=>({ok:true,json:async()=>response}),setTimeout:()=>1,clearTimeout:()=>{},
   videoSequences:{current:{}},videoControllers:{current:{}},setFiles:fn=>files=fn(files),setVideoInfo:()=>{},setFileErrors:fn=>errors=fn(errors),setChecking:fn=>checking=fn(checking),requestErrorMessage:problem=>problem.message});
  vm.runInContext(code,context);await context.selectVideo('pose_video',{type:'video/mp4',size:10});
  assert.equal(files.pose_video,'기존');assert.ok(errors.pose_video);assert.equal(checking.pose_video,false);
 }
});

test('VACE의 이전 영상 응답은 새 선택을 덮어쓰지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/VacePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function inspectVideo('),source.indexOf('  const attachments='));
 let finish,files={},infos={},errors={},checking={},calls=0;
 const context=vm.createContext({AbortController,untilAborted,fetch:()=>++calls===1?new Promise(resolve=>finish=resolve):Promise.resolve({ok:true,json:async()=>({maximum_frames:21,summary:'새 영상'})}),
  setTimeout:()=>1,clearTimeout:()=>{},videoSequences:{current:{}},videoControllers:{current:{}},
  setFiles:fn=>files=fn(files),setVideoInfo:fn=>infos=fn(infos),setFileErrors:fn=>errors=fn(errors),setChecking:fn=>checking=fn(checking),requestErrorMessage:problem=>problem.message});
 vm.runInContext(code,context);const old={type:'video/mp4',size:10},current={type:'video/mp4',size:20};
 const pending=context.selectVideo('pose_video',old);await context.selectVideo('pose_video',current);
 finish({ok:true,json:async()=>({maximum_frames:81,summary:'이전 영상'})});await pending;
 assert.equal(files.pose_video,current);assert.equal(infos.pose_video.summary,'새 영상');assert.equal(errors.pose_video,'');assert.equal(checking.pose_video,false);
});

test('Fun Control 화면 종료 후 인코딩이 끝나도 영상 정보 조회를 시작하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/FunControlPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function attach('),source.indexOf('  async function load('));
 let finish,fetches=0,updates=0;
 const context=vm.createContext({attachmentEpoch:{current:0},attachmentProcessing:{current:false},attachmentRevision:{current:0},poseInspection:{current:null},
  videoData:()=>new Promise(resolve=>finish=resolve),setBusy:()=>updates++,setError:()=>updates++,setPoseError:()=>updates++,clearTimeout:()=>{},fetch:()=>fetches++});
 vm.runInContext(code,context);const pending=context.attach({},'pose_video');const before=updates;
 context.attachmentEpoch.current++;finish('늦은 입력');assert.equal(await pending,false);
 assert.equal(fetches,0);assert.equal(updates,before);
});

test('Fun Control 화면 종료 시 진행 중인 영상 정보 응답과 오류를 무시한다',async()=>{
 const source=readFileSync(new URL('../../gui/FunControlPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function attach('),source.indexOf('  async function load('));
 const cleanupLine=source.split('\n').find(line=>line.includes('useEffect(()=>()=>{attachmentEpoch.current++'));
 let cleanup,finish,updates=0;
 const context=vm.createContext({AbortController,untilAborted,attachmentEpoch:{current:0},attachmentProcessing:{current:false},attachmentRevision:{current:0},poseInspection:{current:null},inputLoading:{current:null},
  useEffect:fn=>cleanup=fn(),videoData:async()=> '영상',fetch:()=>new Promise(resolve=>finish=resolve),setTimeout:()=>1,clearTimeout:()=>{},
  setBusy:()=>updates++,setError:()=>updates++,setPoseError:()=>updates++,setRequest:()=>updates++,setVideoInfo:()=>updates++,requestErrorMessage:problem=>problem.message});
 vm.runInContext(cleanupLine+'\n'+code,context);const pending=context.attach({},'pose_video');
 await new Promise(resolve=>setImmediate(resolve));const before=updates;cleanup();finish({ok:true,json:async()=>({maximum_frames:81,summary:'확인'})});
 assert.equal(await pending,false);assert.equal(updates,before);
});
