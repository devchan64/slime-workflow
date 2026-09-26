'use strict';
// 원본 두 종류는 디코딩 완료 후 같은 프레임을 그려 비동기 이미지의 어긋남을 막는다.
const assetElementLookup=elementIdentifier=>document.getElementById(elementIdentifier);
const assetImageCacheLimit=8;
let assetMotionRecord=null,assetFramePosition=0,assetPlaybackRunning=false,assetPlaybackTimer=null,assetSelectionVersion=0,assetRenderVersion=0;
const assetImagePromiseCache=new Map();
function stopMotionAssetPlayback(){assetPlaybackRunning=false;clearTimeout(assetPlaybackTimer);assetPlaybackTimer=null;}
function loadMotionAssetImages(framePositionValue){
 const selectedDirectionName=assetElementLookup('asset-direction-choice').value;
 const imageCacheIdentifier=`${assetMotionRecord.id}/${selectedDirectionName}/${framePositionValue}`;
 if(!assetImagePromiseCache.has(imageCacheIdentifier)){
  const imageLoadPromise=Promise.all(['openpose','anny'].map(async sourceKindValue=>{const sourceFrameImage=new Image();sourceFrameImage.src=`/character-animation/asset/${assetMotionRecord.id}/${sourceKindValue}/${selectedDirectionName}/${framePositionValue+1}`;await sourceFrameImage.decode();return sourceFrameImage;}));
  assetImagePromiseCache.set(imageCacheIdentifier,imageLoadPromise);
  while(assetImagePromiseCache.size>assetImageCacheLimit)assetImagePromiseCache.delete(assetImagePromiseCache.keys().next().value);
 }
 return assetImagePromiseCache.get(imageCacheIdentifier);
}
async function renderMotionAssetFrame(){
 if(!assetMotionRecord)return false;
 const currentSelectionVersion=assetSelectionVersion,currentRenderVersion=++assetRenderVersion;
 assetFramePosition=(assetFramePosition+assetMotionRecord.frames)%assetMotionRecord.frames;
 const requestedFramePosition=assetFramePosition;
 try{
  const sourceFrameImages=await loadMotionAssetImages(requestedFramePosition);
  if(currentSelectionVersion!==assetSelectionVersion||currentRenderVersion!==assetRenderVersion)return false;
  ['openpose','anny'].forEach((sourceKindValue,sourceImageIndex)=>{const sourceFrameCanvas=assetElementLookup(`asset-${sourceKindValue}-frame`),sourceCanvasContext=sourceFrameCanvas.getContext('2d');sourceCanvasContext.clearRect(0,0,512,512);sourceCanvasContext.drawImage(sourceFrameImages[sourceImageIndex],0,0,512,512);});
  assetElementLookup('asset-frame-position').value=requestedFramePosition;
  assetElementLookup('asset-frame-label').textContent=`${requestedFramePosition+1} / ${assetMotionRecord.frames} · ${assetElementLookup('asset-playback-fps').value} FPS · ${assetElementLookup('asset-playback-speed').value}배`;
  assetElementLookup('asset-playback-status').textContent=assetPlaybackRunning?'원본 에셋 재생 중 · OpenPose / ANNY 동기 재생':'정지 · 같은 프레임의 관절과 외형을 비교하세요.';
  for(const elementIdentifier of ['asset-frame-previous','asset-frame-play','asset-frame-stop','asset-frame-next','asset-frame-position'])assetElementLookup(elementIdentifier).disabled=false;
  // 다음 프레임만 미리 읽어 긴 스트레칭에서도 메모리 사용량을 제한한다.
  loadMotionAssetImages((requestedFramePosition+1)%assetMotionRecord.frames).catch(()=>{});
  return true;
 }catch(frameLoadErrorValue){
  if(currentSelectionVersion!==assetSelectionVersion||currentRenderVersion!==assetRenderVersion)return false;
  stopMotionAssetPlayback();assetElementLookup('asset-playback-status').textContent='에셋 프레임 로딩 실패 · 방향이나 모션을 다시 선택하세요.';return false;
 }
}
function resetMotionAssetPreview(){
 stopMotionAssetPlayback();assetSelectionVersion++;assetRenderVersion++;assetFramePosition=0;assetImagePromiseCache.clear();
 for(const elementIdentifier of ['asset-frame-previous','asset-frame-play','asset-frame-stop','asset-frame-next','asset-frame-position'])assetElementLookup(elementIdentifier).disabled=true;
 for(const sourceKindValue of ['openpose','anny'])assetElementLookup(`asset-${sourceKindValue}-frame`).getContext('2d').clearRect(0,0,512,512);
 assetElementLookup('asset-frame-position').max=assetMotionRecord.frames-1;assetElementLookup('asset-frame-position').value=0;assetElementLookup('asset-frame-label').textContent='';
 assetElementLookup('asset-playback-status').textContent='원본 프레임을 불러오는 중…';renderMotionAssetFrame();
}
window.selectMotionAssetPreview=motionRecordValue=>{
 if(assetMotionRecord?.id===motionRecordValue.id)return;
 assetMotionRecord=motionRecordValue;
 assetElementLookup('asset-motion-title').textContent=`${motionRecordValue.label} · 원본 ${motionRecordValue.frames}프레임 · 기준 ${motionRecordValue.fps} FPS에서 ${motionRecordValue.frames/motionRecordValue.fps}초`;
 resetMotionAssetPreview();
};
assetElementLookup('asset-direction-choice').onchange=()=>{if(assetMotionRecord)resetMotionAssetPreview();};
assetElementLookup('asset-frame-play').onclick=()=>{
 if(!assetMotionRecord||assetPlaybackRunning)return;
 assetPlaybackRunning=true;const playbackSelectionVersion=assetSelectionVersion;
 const advanceMotionAssetFrame=async()=>{
  if(!assetPlaybackRunning||playbackSelectionVersion!==assetSelectionVersion)return;
  const frameStartTimestamp=performance.now();assetFramePosition++;
  if(await renderMotionAssetFrame()&&assetPlaybackRunning&&playbackSelectionVersion===assetSelectionVersion)assetPlaybackTimer=setTimeout(advanceMotionAssetFrame,Math.max(0,1000/(Number(assetElementLookup('asset-playback-fps').value)*Number(assetElementLookup('asset-playback-speed').value))-(performance.now()-frameStartTimestamp)));
 };
 assetPlaybackTimer=setTimeout(advanceMotionAssetFrame,1000/(Number(assetElementLookup('asset-playback-fps').value)*Number(assetElementLookup('asset-playback-speed').value)));
};
assetElementLookup('asset-frame-stop').onclick=()=>{stopMotionAssetPlayback();assetRenderVersion++;assetFramePosition=Number(assetElementLookup('asset-frame-position').value);assetElementLookup('asset-playback-status').textContent='정지 · 같은 프레임의 관절과 외형을 비교하세요.';};
for(const [elementIdentifier,frameIncrementValue] of [['asset-frame-previous',-1],['asset-frame-next',1]])assetElementLookup(elementIdentifier).onclick=()=>{stopMotionAssetPlayback();assetFramePosition+=frameIncrementValue;renderMotionAssetFrame();};
assetElementLookup('asset-frame-position').oninput=()=>{stopMotionAssetPlayback();assetFramePosition=Number(assetElementLookup('asset-frame-position').value);renderMotionAssetFrame();};
document.addEventListener('visibilitychange',()=>{if(document.hidden)assetElementLookup('asset-frame-stop').click();});

assetElementLookup('asset-playback-fps').onchange=()=>{if(!assetMotionRecord)return;assetElementLookup('asset-frame-label').textContent=`${Number(assetElementLookup('asset-frame-position').value)+1} / ${assetMotionRecord.frames} · ${assetElementLookup('asset-playback-fps').value} FPS · ${assetElementLookup('asset-playback-speed').value}배`;};

assetElementLookup('asset-playback-speed').onchange=()=>assetElementLookup('asset-playback-fps').onchange();
