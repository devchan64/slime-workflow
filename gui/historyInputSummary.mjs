export function historyInputSummary(request, service="") {
  if (!request || typeof request!=="object" || Array.isArray(request)) return [];
  const result=[];
  if (typeof request.tag==="string" && request.tag.trim()) result.push(`태그 ${request.tag.trim()}`);
  if (Number.isInteger(request.width) && request.width>0 && Number.isInteger(request.height) && request.height>0) result.push(`${request.width} × ${request.height}`);
  if (typeof request.duration_seconds==="number" && Number.isFinite(request.duration_seconds) && request.duration_seconds>0) result.push(`길이 ${request.duration_seconds}초`);
  if (request.audio_available===true) result.push("WAV 오디오 결과");
  if (service!=="dwpose" && Number.isInteger(request.frames) && request.frames>0) result.push(`${request.frames}프레임`);
  if (service!=="dwpose" && Number.isInteger(request.steps) && request.steps>0) result.push(`${request.steps}스텝`);
  if (service==="minimax-h3-image" && (request.sampler===undefined || request.sampler==="euler" || request.sampler==="lcm")) result.push(request.sampler==="lcm" ? "LCM · 실험" : "Euler");
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
    return typeof value==='string' && (value.startsWith('data:') || value.length>10000) ? '[첨부 또는 긴 데이터 생략]' : value;
  },2);
}
