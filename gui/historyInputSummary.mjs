export function historyInputSummary(request, service="") {
  if (!request || typeof request!=="object" || Array.isArray(request)) return [];
  const result=[];
  if (typeof request.tag==="string" && request.tag.trim()) result.push(`태그 ${request.tag.trim()}`);
  if (Number.isInteger(request.width) && request.width>0 && Number.isInteger(request.height) && request.height>0) result.push(`${request.width} × ${request.height}`);
  if (typeof request.duration_seconds==="number" && Number.isFinite(request.duration_seconds) && request.duration_seconds>0) result.push(`길이 ${request.duration_seconds}초`);
  if (request.audio_available===true) result.push("WAV 오디오 결과");
  if (service!=="dwpose" && Number.isInteger(request.frames) && request.frames>0) result.push(`${request.frames}프레임`);
  if (service!=="dwpose" && Number.isInteger(request.steps) && request.steps>0) result.push(`${request.steps}스텝`);
  if (service!=="dwpose" && Number.isInteger(request.seed) && request.seed>=0) result.push(`시드 ${request.seed}`);
  if (typeof request.pose_include_hands==="boolean") result.push(`손 상세 ${request.pose_include_hands ? "포함" : "제외"}`);
  if (typeof request.pose_include_face==="boolean") result.push(`얼굴 상세 ${request.pose_include_face ? "포함" : "제외"}`);
  return result;
}
