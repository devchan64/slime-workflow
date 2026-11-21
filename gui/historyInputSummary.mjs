export function historyInputSummary(request) {
  if (!request || typeof request!=="object" || Array.isArray(request)) return [];
  const result=[];
  if (typeof request.tag==="string" && request.tag.trim()) result.push(`태그 ${request.tag.trim()}`);
  if (Number.isInteger(request.width) && request.width>0 && Number.isInteger(request.height) && request.height>0) result.push(`${request.width} × ${request.height}`);
  if (Number.isInteger(request.frames) && request.frames>0) result.push(`${request.frames}프레임`);
  if (Number.isInteger(request.steps) && request.steps>0) result.push(`${request.steps}스텝`);
  if (Number.isInteger(request.seed) && request.seed>=0) result.push(`시드 ${request.seed}`);
  return result;
}
