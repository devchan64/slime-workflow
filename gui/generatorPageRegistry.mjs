/** 공통 페이지 식별 정보. 이 등록은 기능 구현·전환 완료를 의미하지 않는다. */
export const generatorPages=Object.freeze({
  dwpose:Object.freeze({title:'DWPose 이미지 추출',changelog:'dwpose-generator'}),
  kimodo:Object.freeze({title:'Kimodo 모션 생성기',changelog:'kimodo-generator'}),
  'wan22-vace':Object.freeze({title:'Wan VACE 영상 생성',changelog:'wan22-vace-generator'}),
  'wan22-i2v':Object.freeze({title:'Wan 2.2 I2V 영상 생성',changelog:'wan22-i2v-generator'}),
});
export function generatorPageIdentity(service){
  if(!Object.hasOwn(generatorPages,service)) throw new Error(`등록되지 않은 생성기 페이지: ${service}`);
  return generatorPages[service];
}
