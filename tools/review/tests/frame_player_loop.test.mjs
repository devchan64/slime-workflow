import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const currentStatusElement={textContent:''};
const currentImageElement={style:{},replaceChildren(){}};
const currentDownloadElement={replaceChildren(){}};
let currentTimerCallback=null;
const currentPlayerContext={
 currentPlayerIdentifier:'test-player',
 props:{value:JSON.stringify({directUrls:true,frames:{first:Array.from({length:24},()=>['test.png'])}})},
 element:{isConnected:true,querySelector(currentSelectorText){return currentSelectorText==='[data-player-status]'?currentStatusElement:currentSelectorText==='[data-player-images]'?currentImageElement:currentDownloadElement;}},
 document:{createElement(){return {append(){},createTHead(){return {insertRow(){return {append(){}};}};},createTBody(){return {rows:[]};}};}},
 window:{},Image:class {},watch(){},setInterval(currentCallbackValue){currentTimerCallback=currentCallbackValue;return 1;},clearInterval(){currentTimerCallback=null;},URL
};
vm.createContext(currentPlayerContext);
vm.runInContext(readFileSync('tools/review/ui/shared/frame-player.js','utf8'),currentPlayerContext);
const currentPlayerCommand=currentPlayerContext.window.generationFramePlayerCommands['test-player'];
assert.match(currentPlayerCommand('loop','first',6,1,7,13),/6 FPS/);
assert.match(currentStatusElement.textContent,/7 \/ 24/);
for(let currentStepIndex=0;currentStepIndex<6;currentStepIndex++)currentTimerCallback();
assert.match(currentStatusElement.textContent,/13 \/ 24/);
currentTimerCallback();assert.match(currentStatusElement.textContent,/7 \/ 24/);
currentPlayerCommand('configure','first',12,1);currentTimerCallback();assert.match(currentStatusElement.textContent,/8 \/ 24/);
currentPlayerCommand('stop','first',12,1);assert.equal(currentTimerCallback,null);
assert.match(currentPlayerCommand('loop','first',8,1,13,7),/시작 ≤ 끝/);
assert.equal(currentTimerCallback,null);
currentPlayerCommand('loop','first',8,1,24,24);currentTimerCallback();assert.match(currentStatusElement.textContent,/24 \/ 24/);
currentPlayerCommand('play','first',8,1);currentTimerCallback();assert.match(currentStatusElement.textContent,/1 \/ 24/);
console.log('구간 반복·경계·FPS 변경·정지·전체 재생 검사 통과');
