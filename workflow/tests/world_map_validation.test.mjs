import {test} from "node:test";
import assert from "node:assert/strict";
import {validWorldMap} from "../../gui/worldMapValidation.mjs";

test("월드맵은 빈 목록과 선택적 도착 지점을 허용하고 손상된 연결은 거부한다",()=>{
  const thumbnail={url:"/image.png",managementId:"image",version:"v1",sha256:"a",path:"image.png"};
  const town={id:"town",name:"마을",safeTown:true,column:0,row:0,thumbnail,connections:[{id:"gate",target:"field",direction:"east"}]};
  const field={id:"field",name:"필드",safeTown:false,column:1,row:0,thumbnail,connections:[]};
  assert.equal(validWorldMap({maps:[]}),true);
  assert.equal(validWorldMap({maps:[town,field]}),true);
  assert.equal(validWorldMap({maps:[town]}),false);
  assert.equal(validWorldMap({maps:[town,town]}),false);
  assert.equal(validWorldMap({maps:[{...field,thumbnail:null}]}),false);
});
