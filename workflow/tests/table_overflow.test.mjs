import test from "node:test";
import assert from "node:assert/strict";
import {observeTableOverflow,scrollTableOnArrow} from "../../gui/observeTableOverflow.mjs";

test("표와 컨테이너의 크기 변화에 따라 넘침을 갱신하고 관찰을 해제한다",()=>{
  const view=new EventTarget(),node=Object.assign(new EventTarget(),{clientWidth:360,scrollWidth:360}),table={},values=[];
  let instance;
  class Observer {constructor(update){this.update=update;this.targets=[];instance=this;} observe(target){this.targets.push(target);} disconnect(){this.disconnected=true;}}
  const stop=observeTableOverflow(node,table,value=>values.push(value),{window:view,Observer});
  assert.deepEqual(values,[false]);assert.deepEqual(instance.targets,[node,table]);
  node.scrollWidth=500;instance.update();assert.equal(values.at(-1),true);
  node.clientWidth=500;view.dispatchEvent(new Event("resize"));assert.equal(values.at(-1),false);
  stop();assert.equal(instance.disconnected,true);const count=values.length;instance.update();view.dispatchEvent(new Event("resize"));assert.equal(values.length,count);
});

test("크기 관찰 기능이 없어도 표 안의 지연 로딩 후 넘침을 갱신한다",()=>{
  const view=new EventTarget(),node=Object.assign(new EventTarget(),{clientWidth:360,scrollWidth:360}),values=[];
  const stop=observeTableOverflow(node,{},value=>values.push(value),{window:view,Observer:undefined});
  node.scrollWidth=500;node.dispatchEvent(new Event("load"));assert.deepEqual(values,[false,true]);
  stop();node.scrollWidth=360;node.dispatchEvent(new Event("load"));assert.deepEqual(values,[false,true]);
});

test("글꼴 로딩 뒤 넘침을 갱신하고 종료 시 구독을 해제한다",()=>{
  const fonts=new EventTarget(),view=new EventTarget(),node=Object.assign(new EventTarget(),{clientWidth:360,scrollWidth:360,ownerDocument:{fonts}}),values=[];
  const stop=observeTableOverflow(node,{},value=>values.push(value),{window:view,Observer:undefined});
  node.scrollWidth=400;fonts.dispatchEvent(new Event("loadingdone"));assert.deepEqual(values,[false,true]);
  stop();node.scrollWidth=360;fonts.dispatchEvent(new Event("loadingdone"));assert.deepEqual(values,[false,true]);
});

test("넘치는 표에서만 방향키로 스크롤하고 내부 입력의 키는 유지한다",()=>{
  const node={clientWidth:360,scrollWidth:500,scrollLeft:0};
  let prevented=false;
  const event={target:node,currentTarget:node,key:"ArrowRight",preventDefault(){prevented=true;}};
  scrollTableOnArrow(event);assert.equal(node.scrollLeft,80);assert.equal(prevented,true);
  prevented=false;event.target={};scrollTableOnArrow(event);assert.equal(node.scrollLeft,80);assert.equal(prevented,false);
  event.target=node;
  for(const modifier of ['altKey','ctrlKey','metaKey','shiftKey']){
    event[modifier]=true;scrollTableOnArrow(event);assert.equal(node.scrollLeft,80);assert.equal(prevented,false);event[modifier]=false;
  }
  event.target=node;node.scrollWidth=360;scrollTableOnArrow(event);assert.equal(node.scrollLeft,80);assert.equal(prevented,false);
});
