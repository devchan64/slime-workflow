import {test} from "node:test";
import assert from "node:assert/strict";
import {validEffectDetail,validWaypointFrames} from "../../gui/effectDetailValidation.mjs";

test("이펙트 상세와 웨이포인트 프레임의 필수 형식을 확인한다",()=>{
  const base={document:{id:"effect",name:"이펙트",renderer:"swarm",frames:8,alignment:{texture:"moths",alpha:.5,target:[0,0,1,1],frames:Array.from({length:8},()=>[0,0,1,1])}},revision:"r",sheetImage:"data:image/png;base64,x",rendererModule:"/renderer.mjs",hostImage:null};
  assert.equal(validEffectDetail(base,"effect"),true);
  assert.equal(validEffectDetail({...base,document:{...base.document,alignment:{...base.document.alignment,frames:[]}}},"effect"),false);
  assert.equal(validEffectDetail(base,"other"),false);
  const frames=[{rect:{x:0,y:0,width:10,height:12},anchor:{x:5,y:10}}];
  assert.equal(validWaypointFrames(frames,1),true);
  assert.equal(validWaypointFrames([{...frames[0],rect:{...frames[0].rect,width:0}}],1),false);
  assert.equal(validWaypointFrames([{}],1),false);
});
