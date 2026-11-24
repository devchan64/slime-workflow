import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('프레임 선택은 재생을 멈추고 표시와 버튼 상태를 갱신한다',()=>{
  const html=readFileSync(new URL('../../gui/ui/asset_review/walk-sheet.html',import.meta.url),'utf8');
  const lines=html.split('\n');
  const selection=lines.find(line=>line.startsWith('function selectReviewFrame'));
  const renderIndex=lines.findIndex(line=>line.startsWith('function renderReviewPanels'));
  const render=lines.slice(renderIndex,renderIndex+2).join('\n');
  const attributes=()=>({attributes:{},setAttribute(name,value){this.attributes[name]=value;}});
  const context2d={clearRect(){},drawImage(){},setLineDash(){},beginPath(){},moveTo(){},lineTo(){},stroke(){}};
  const canvas={width:600,height:600,getContext:()=>context2d};
  const frameButtons=Array.from({length:8},()=>({...attributes(),querySelector:()=>canvas}));
  const directionButtons=['down_left','up_right'].map(direction=>({...attributes(),dataset:{direction}}));
  const elements={'#feet':{checked:false},'#overlay':{checked:false},'#guides':{checked:false},'#character':canvas,'#rig':canvas,
    '#frameLabel':attributes(),'#play':{},'#sheetLink':{},'#rigLink':{},'#details':{}};
  const state=vm.createContext({reviewAssetRecords:[{direction:'down_left',image:'walk.png',size:[256,256]}],
    loadedSheetImages:{'walk.png':{},'rig-down_left.png':{}},selectedDirectionName:'down_left',selectedFrameIndex:0,
    animationPlaybackActive:true,reviewFrameCount:8,reviewCanvasSize:600,frameButtonElements:frameButtons,directionButtonElements:directionButtons,
    directionLabelNames:{down_left:'좌하'},document:{querySelector:selector=>elements[selector]},drawSheetFrame:()=>{}});
  vm.runInContext(selection+'\n'+render,state);
  vm.runInContext('selectReviewFrame(7)',state);
  assert.equal(state.animationPlaybackActive,false);assert.equal(state.selectedFrameIndex,7);
  assert.equal(elements['#frameLabel'].textContent,'8 / 8 프레임');assert.equal(elements['#frameLabel'].attributes['aria-live'],'polite');
  assert.equal(elements['#play'].textContent,'재생');assert.equal(frameButtons[7].attributes['aria-pressed'],'true');
  assert.equal(frameButtons[0].attributes['aria-pressed'],'false');assert.equal(directionButtons[0].attributes['aria-pressed'],'true');
  assert.equal(elements['#sheetLink'].href,'walk.png');assert.equal(elements['#rigLink'].href,'rig-down_left.png');
  vm.runInContext('selectReviewFrame(-1)',state);assert.equal(state.selectedFrameIndex,7);
  state.animationPlaybackActive=true;vm.runInContext('renderReviewPanels()',state);
  assert.equal(elements['#frameLabel'].attributes['aria-live'],'off');assert.equal(elements['#play'].textContent,'일시정지');
});
