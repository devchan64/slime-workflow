export function historyInputSummary(request, service="") {
  if (!request || typeof request!=="object" || Array.isArray(request)) return [];
  const result=[];
  if (typeof request.tag==="string" && request.tag.trim()) result.push(`태그 ${request.tag.trim()}`);
  if (Number.isInteger(request.width) && request.width>0 && Number.isInteger(request.height) && request.height>0) result.push(`${request.width} × ${request.height}`);
  if (typeof request.duration_seconds==="number" && Number.isFinite(request.duration_seconds) && request.duration_seconds>0) result.push(`길이 ${request.duration_seconds}초`);
  if (request.audio_available===true) result.push("WAV 오디오 결과");
  if (service!=="dwpose" && Number.isInteger(request.frames) && request.frames>0) result.push(`${request.frames}프레임`);
  if (service!=="dwpose" && Number.isInteger(request.steps) && request.steps>0) result.push(`${request.steps}스텝`);
  if (service==="minimax-h3-image") result.push(request.sampler==="euler" ? "Euler" : request.sampler==="lcm" ? "LCM · 실험" : "샘플러 확인 필요");
  if (service!=="dwpose" && Number.isInteger(request.seed) && request.seed>=0) result.push(`시드 ${request.seed}`);
  if (["wan21-i2v","wan21-t2v"].includes(service) && typeof request.action_lora==="boolean") {
    if (!request.action_lora) result.push("동작 LoRA 사용 안 함");
    else {
      const variants={fight:service==="wan21-t2v" ? "KXSR" : "Fight",attack_high:"Attack Sprite high",attack_low:"Attack Sprite low"};
      const name=request.action_variant ?? "fight";
      const variant=Object.hasOwn(variants,name) ? variants[name] : "";
      if (variant) result.push(`동작 LoRA ${variant}${typeof request.action_strength==="number" && Number.isFinite(request.action_strength) ? ` · 강도 ${request.action_strength}` : ""}`);
      else result.push("동작 LoRA 종류 확인 필요");
    }
  }
  if (typeof request.pose_include_hands==="boolean") result.push(`손 상세 ${request.pose_include_hands ? "포함" : "제외"}`);
  if (typeof request.pose_include_face==="boolean") result.push(`얼굴 상세 ${request.pose_include_face ? "포함" : "제외"}`);
  return result;
}

export function historyInputDetails(request){
  return JSON.stringify(request,(key,value)=>{
    if(key==='images' && Array.isArray(value))return value.map(item=>
      typeof item==='string' && (item.startsWith('data:') || /^(?:iVBORw0KGgo|\/9j\/|R0lGOD|UklGR|Qk0)/.test(item)) ? '[이미지 데이터 생략]' : item);
    if(['edit_video','driving_video','pose_video','edit_mask'].includes(key) && typeof value==='string' && value.length>100 && /^[A-Za-z0-9+/=]+$/.test(value))return '[영상 데이터 생략]';
    return typeof value==='string' && (value.startsWith('data:') || value.length>10000) ? '[첨부 또는 긴 데이터 생략]' : value;
  },2);
}

/** 미리보기에서 이미 표시한 최상위 필드만 제외하고 나머지 설정은 보존한다. */
export function historyInputAdditionalSettings(request, service="") {
  if (!request || typeof request !== "object" || Array.isArray(request)) return {};
  const rest={...request};
  for (const key of ["user_prompt","prompt","negative_prompt","translation_source_ko"]) {
    if (typeof request[key] === "string" && request[key].trim()) delete rest[key];
  }
  if (Array.isArray(request.images) && request.images.length && request.images.every(value=>typeof value==="string" && value)) delete rest.images;
  for (const key of ["edit_video","driving_video","pose_video","edit_mask"]) {
    if (typeof request[key] === "string" && request[key]) delete rest[key];
  }
  if (typeof request.tag === "string" && request.tag.trim()) delete rest.tag;
  if (Number.isInteger(request.width) && request.width>0 && Number.isInteger(request.height) && request.height>0) { delete rest.width; delete rest.height; }
  if (typeof request.duration_seconds==="number" && Number.isFinite(request.duration_seconds) && request.duration_seconds>0) delete rest.duration_seconds;
  if (request.audio_available===true) delete rest.audio_available;
  if (service!=="dwpose") for (const key of ["frames","steps"]) if (Number.isInteger(request[key]) && request[key]>0) delete rest[key];
  if (service!=="dwpose" && Number.isInteger(request.seed) && request.seed>=0) delete rest.seed;
  if (typeof request.pose_include_hands==="boolean") delete rest.pose_include_hands;
  if (typeof request.pose_include_face==="boolean") delete rest.pose_include_face;
  if (service==="minimax-h3-image") delete rest.sampler;
  return rest;
}
