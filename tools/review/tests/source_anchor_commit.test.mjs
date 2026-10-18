import test from 'node:test';
import assert from 'node:assert/strict';
import {installSourceSizePreview} from '../ui/map/source-size-preview.js';

test('연속 저장은 성공한 공통 속성을 기대값으로 사용한다',()=>{
 globalThis.window={};
 const currentMapRecord={id:'sample',safeTown:false,objects:[{id:'one',textureKey:'grass',anchorX:0.5,anchorY:0.94,displayHeight:64}]};
 installSourceSizePreview({}, {},currentMapRecord);
 const currentFirstPayload=window.mapSourceAnchorPayload('grass',0.5,0.9,1,1,57);
 window.mapSourceAnchorCommitted({saved:true,payload:currentFirstPayload});
 const currentNextPayload=window.mapSourceAnchorPayload('grass',0.5,0.9,1,1,60);
 assert.equal(currentNextPayload.expected[0].displayHeight,57);
 assert.equal(currentNextPayload.expected[0].anchorY,0.9);
 window.mapSourceAnchorCommitted({saved:false,payload:currentNextPayload});
 assert.equal(window.mapSourceAnchorRead('grass')[4],57);
 window.mapSourceAnchorCommitted({saved:true,payload:{...currentNextPayload,map:'another'}});
 assert.equal(window.mapSourceAnchorRead('grass')[4],57);
});
