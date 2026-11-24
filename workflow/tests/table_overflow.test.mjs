import test from "node:test";
import assert from "node:assert/strict";
import {observeTableOverflow} from "../../gui/observeTableOverflow.mjs";

test("표와 컨테이너의 크기 변화에 따라 넘침을 갱신하고 관찰을 해제한다",()=>{
  const view=new EventTarget(),node={clientWidth:360,scrollWidth:360},table={},values=[];
  let instance;
  class Observer {constructor(update){this.update=update;this.targets=[];instance=this;} observe(target){this.targets.push(target);} disconnect(){this.disconnected=true;}}
  const stop=observeTableOverflow(node,table,value=>values.push(value),{window:view,Observer});
  assert.deepEqual(values,[false]);assert.deepEqual(instance.targets,[node,table]);
  node.scrollWidth=500;instance.update();assert.equal(values.at(-1),true);
  node.clientWidth=500;view.dispatchEvent(new Event("resize"));assert.equal(values.at(-1),false);
  stop();assert.equal(instance.disconnected,true);const count=values.length;instance.update();view.dispatchEvent(new Event("resize"));assert.equal(values.length,count);
});
