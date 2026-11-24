// All required videos must be inspected before their shared output limit is known.
export function videoFrameLimit(keys, info) {
  if (!keys.length) return null;
  const limits=keys.map(key=>info[key]?.maximum_frames);
  return limits.every(value=>Number.isInteger(value) && value>=5) ? Math.min(...limits) : null;
}

/** Animate-2 영상 정보는 표시와 프레임 제한에 함께 사용한다. */
export function validAnimateVideoInfo(info) {
  return Boolean(info && Number.isInteger(info.maximum_frames) && info.maximum_frames>=5 && info.maximum_frames<=81 && (info.maximum_frames-1)%4===0 &&
    Number.isInteger(info.width) && info.width>0 && Number.isInteger(info.height) && info.height>0 &&
    Number.isInteger(info.frame_count) && info.frame_count>0 && Number.isFinite(info.fps) && info.fps>=1 && info.fps<=120);
}
