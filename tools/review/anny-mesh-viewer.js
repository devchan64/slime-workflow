// ANNY 원본 Z-up 메시를 화면의 수직축으로 투영한다.
class AnnyMeshPreview {
 constructor(previewCanvasElement) {
  this.previewCanvasElement=previewCanvasElement;
  const previewWebglContext=previewCanvasElement.getContext('webgl2');
  if(!previewWebglContext)throw Error('웹 3D 프리뷰에 WebGL2가 필요합니다.');
  this.previewWebglContext=previewWebglContext;
  const compilePreviewShader=(shaderTypeValue,shaderSourceText)=>{
   const compiledShaderObject=previewWebglContext.createShader(shaderTypeValue);
   previewWebglContext.shaderSource(compiledShaderObject,shaderSourceText);previewWebglContext.compileShader(compiledShaderObject);
   if(!previewWebglContext.getShaderParameter(compiledShaderObject,previewWebglContext.COMPILE_STATUS))throw Error(previewWebglContext.getShaderInfoLog(compiledShaderObject));return compiledShaderObject;
  };
  this.previewShaderProgram=previewWebglContext.createProgram();
  previewWebglContext.attachShader(this.previewShaderProgram,compilePreviewShader(previewWebglContext.VERTEX_SHADER,`#version 300 es
  in vec3 position; uniform vec3 center; uniform vec4 view; out vec3 surfacePoint;
  void main(){vec3 p=position-center;float x=cos(view.x)*p.x-sin(view.x)*p.y;float y=sin(view.x)*p.x+cos(view.x)*p.y;float z=cos(view.y)*p.z-sin(view.y)*y;float d=sin(view.y)*p.z+cos(view.y)*y;surfacePoint=vec3(x,d,z);gl_Position=vec4(x*view.z/view.w,z*view.z,d*view.z*.1,1.);}`));
  previewWebglContext.attachShader(this.previewShaderProgram,compilePreviewShader(previewWebglContext.FRAGMENT_SHADER,`#version 300 es
  precision highp float;in vec3 surfacePoint;out vec4 color;
  void main(){vec3 n=normalize(cross(dFdx(surfacePoint),dFdy(surfacePoint)));float light=.35+.65*abs(dot(n,normalize(vec3(.4,-.7,.8))));color=vec4(vec3(.68,.79,.73)*light,1.);}`));
  previewWebglContext.linkProgram(this.previewShaderProgram);
  if(!previewWebglContext.getProgramParameter(this.previewShaderProgram,previewWebglContext.LINK_STATUS))throw Error('웹 프리뷰 셰이더 연결 실패');
  this.previewYawRadians=0;this.previewPitchRadians=0;this.previewZoomFactor=1;this.previewTriangleCount=0;
  let previousPointerPoint=null;
  previewCanvasElement.onpointerdown=pointerInputEvent=>{previousPointerPoint=[pointerInputEvent.clientX,pointerInputEvent.clientY];previewCanvasElement.setPointerCapture(pointerInputEvent.pointerId)};
  previewCanvasElement.onpointerup=()=>previousPointerPoint=null;
  previewCanvasElement.onpointercancel=()=>previousPointerPoint=null;
  previewCanvasElement.onpointermove=pointerInputEvent=>{if(!previousPointerPoint)return;this.previewYawRadians+=(pointerInputEvent.clientX-previousPointerPoint[0])*.01;this.previewPitchRadians=Math.max(-1.2,Math.min(1.2,this.previewPitchRadians+(pointerInputEvent.clientY-previousPointerPoint[1])*.01));previousPointerPoint=[pointerInputEvent.clientX,pointerInputEvent.clientY];this.drawPreviewMesh()};
  previewCanvasElement.addEventListener('wheel',pointerInputEvent=>{pointerInputEvent.preventDefault();this.previewZoomFactor=Math.max(.4,Math.min(3,this.previewZoomFactor*Math.exp(-pointerInputEvent.deltaY*.001)));this.drawPreviewMesh()},{passive:false});
  new ResizeObserver(()=>this.drawPreviewMesh()).observe(previewCanvasElement);
 }
 setPreviewRotation(rotationDegreeValue){this.previewYawRadians=rotationDegreeValue*Math.PI/180;this.drawPreviewMesh()}
 async loadPreviewRecord(generationRecordId){
  const meshFetchResponse=await fetch('/anny-attributes/jobs/'+generationRecordId+'/mesh.json');if(!meshFetchResponse.ok)throw Error('저장된 3D 메시를 불러올 수 없습니다.');
  const meshPayloadValues=await meshFetchResponse.json();
  const previewWebglContext=this.previewWebglContext;
  const vertexFlatValues=meshPayloadValues.vertices.flat();
  this.previewCenterValues=[0,1,2].map(axisIndexValue=>{const axisVertexValues=meshPayloadValues.vertices.map(vertexPointValues=>vertexPointValues[axisIndexValue]);return (Math.min(...axisVertexValues)+Math.max(...axisVertexValues))/2});
  const verticalVertexValues=meshPayloadValues.vertices.map(vertexPointValues=>vertexPointValues[2]);this.previewHeightValue=Math.max(...verticalVertexValues)-Math.min(...verticalVertexValues);
  previewWebglContext.useProgram(this.previewShaderProgram);
  if(this.previewVertexBuffer)previewWebglContext.deleteBuffer(this.previewVertexBuffer);
  if(this.previewIndexBuffer)previewWebglContext.deleteBuffer(this.previewIndexBuffer);
  this.previewVertexBuffer=previewWebglContext.createBuffer();previewWebglContext.bindBuffer(previewWebglContext.ARRAY_BUFFER,this.previewVertexBuffer);previewWebglContext.bufferData(previewWebglContext.ARRAY_BUFFER,new Float32Array(vertexFlatValues),previewWebglContext.STATIC_DRAW);
  const positionAttributeIndex=previewWebglContext.getAttribLocation(this.previewShaderProgram,'position');previewWebglContext.enableVertexAttribArray(positionAttributeIndex);previewWebglContext.vertexAttribPointer(positionAttributeIndex,3,previewWebglContext.FLOAT,false,0,0);
  this.previewIndexBuffer=previewWebglContext.createBuffer();previewWebglContext.bindBuffer(previewWebglContext.ELEMENT_ARRAY_BUFFER,this.previewIndexBuffer);const triangleIndexValues=meshPayloadValues.faces.flat();previewWebglContext.bufferData(previewWebglContext.ELEMENT_ARRAY_BUFFER,new Uint32Array(triangleIndexValues),previewWebglContext.STATIC_DRAW);this.previewTriangleCount=triangleIndexValues.length;this.drawPreviewMesh();
 }
 drawPreviewMesh(){
  if(!this.previewTriangleCount)return;
  const previewWebglContext=this.previewWebglContext,previewCanvasElement=this.previewCanvasElement;
  previewCanvasElement.width=previewCanvasElement.clientWidth*devicePixelRatio;previewCanvasElement.height=previewCanvasElement.clientHeight*devicePixelRatio;
  previewWebglContext.viewport(0,0,previewCanvasElement.width,previewCanvasElement.height);previewWebglContext.clearColor(.045,.075,.06,1);previewWebglContext.clear(previewWebglContext.COLOR_BUFFER_BIT|previewWebglContext.DEPTH_BUFFER_BIT);previewWebglContext.enable(previewWebglContext.DEPTH_TEST);previewWebglContext.useProgram(this.previewShaderProgram);
  previewWebglContext.uniform3fv(previewWebglContext.getUniformLocation(this.previewShaderProgram,'center'),this.previewCenterValues);previewWebglContext.uniform4f(previewWebglContext.getUniformLocation(this.previewShaderProgram,'view'),this.previewYawRadians,this.previewPitchRadians,1.7/this.previewHeightValue*this.previewZoomFactor,previewCanvasElement.width/previewCanvasElement.height);previewWebglContext.drawElements(previewWebglContext.TRIANGLES,this.previewTriangleCount,previewWebglContext.UNSIGNED_INT,0);
 }
}
