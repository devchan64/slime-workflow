(currentPreviewClip,currentSourceRecord,currentFrameIndex)=>{
 // 동작 선택은 재생을 멈추고 해당 동작의 첫 원본 프레임으로 이동한다.
 if(!currentPreviewClip)return [false,1];
 const currentAnimationRecord=currentSourceRecord?.animation;
 const currentClipRecord=currentAnimationRecord?.clips?.find(currentClipValue=>currentClipValue.clipId===currentPreviewClip);
 const currentFirstFrame=currentClipRecord?.frames?.[0];
 const currentFirstIndex=currentAnimationRecord?.frames?.findIndex(currentFrameValue=>currentFrameValue.frameId===currentFirstFrame?.frameId);
 if(!Number.isInteger(currentFirstIndex)||currentFirstIndex<0)return [false,currentFrameIndex];
 return [false,currentFirstIndex+1];
}
