import {test} from "node:test";
import assert from "node:assert/strict";
import {validWorldMap,worldMapLinks} from "../../gui/worldMapValidation.mjs";

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

test("지도 간 연결은 방향과 중복에 관계없이 한 번씩 표시한다",()=>{
  const maps=[{id:"z",connections:[{target:"a"},{target:"a"}]},{id:"a",connections:[{target:"z"},{target:"b"}]},{id:"b",connections:[]}];
  assert.deepEqual(worldMapLinks(maps),[["a","z"],["a","b"]]);
  assert.deepEqual(worldMapLinks([{id:"z",connections:[{target:"a"}]},{id:"a",connections:[]}]),[["a","z"]]);
});
