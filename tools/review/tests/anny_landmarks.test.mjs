// 브라우저 투영과 가시 표면 선택의 기하학 검증. WebGL 렌더 자체는 브라우저에서 검수한다.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const currentVmContext=vm.createContext({window:{},AnnyMeshPreview:class {}});
vm.runInContext(fs.readFileSync(new URL('../ui/anny/anny-landmarks.js',import.meta.url),'utf8')+'\nwindow.LandmarkPreviewClass=AnnyLandmarkPreview;',currentVmContext);
const currentPreviewObject=Object.create(currentVmContext.window.LandmarkPreviewClass.prototype);
Object.assign(currentPreviewObject,{previewCenterValues:[0,0,0],previewYawRadians:0,previewPitchRadians:0,previewZoomFactor:1,previewHeightValue:1.7,previewCanvasElement:{clientWidth:200,clientHeight:200}});
assert.deepEqual(Array.from(currentPreviewObject.projectCandidatePoint([.5,-.2,.5])),[150,50,-.2]);
currentPreviewObject.currentSourceRecord={vertices:[[-.5,-.2,-.5],[.5,-.2,-.5],[0,-.2,.5],[-.5,.2,-.5],[.5,.2,-.5],[0,.2,.5]],faces:[[3,4,5],[0,1,2]]};
assert.equal(currentPreviewObject.pickVisibleVertex([100,60])[1],-.2,'가까운 면을 선택해야 함');
assert.equal(currentPreviewObject.pickVisibleVertex([0,0]),null,'빈 공간은 선택하지 않음');
currentPreviewObject.previewYawRadians=Math.PI;
assert.equal(currentPreviewObject.pickVisibleVertex([100,60])[1],.2,'후면에서 반대쪽 면 선택');
console.log('ANNY 투영·가시 삼각형·후면 선택 검사 통과');
