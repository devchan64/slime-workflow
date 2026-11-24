export function effectAlignmentBoundsIssue(alignment){
  const validate=(row,label)=>{
    if(!Array.isArray(row) || row.length!==4)return `${label}: 좌표 4개가 필요합니다.`;
    const values=row.map(value=>typeof value==="number" ? value : typeof value==="string" && value.trim() ? Number(value) : NaN);
    const names=["왼쪽","위쪽","오른쪽","아래쪽"];
    for(let index=0;index<4;index++)if(!Number.isFinite(values[index]) || values[index]<0 || values[index]>1)return `${label} · ${names[index]}: 0~1 사이 숫자를 입력하세요.`;
    if(values[0]>=values[2] || values[1]>=values[3])return `${label}: 왼쪽 < 오른쪽, 위쪽 < 아래쪽이어야 합니다.`;
    return "";
  };
  const targetError=validate(alignment?.target,"대상 영역");
  if(targetError)return {group:"target",message:targetError};
  if(!Array.isArray(alignment.frames) || alignment.frames.length!==8)return {group:null,message:"프레임 영역은 8개가 필요합니다."};
  for(let index=0;index<alignment.frames.length;index++){
    const error=validate(alignment.frames[index],`프레임 ${index+1}`);
    if(error)return {group:`frame:${index}`,message:error};
  }
  return null;
}

export function effectAlignmentBoundsError(alignment){return effectAlignmentBoundsIssue(alignment)?.message || "";}
