export function invalidSpriteGridCount(value){
  return value==null || String(value).trim()==='' || !Number.isInteger(Number(value)) || Number(value)<1 || Number(value)>128;
}
export function invalidSpriteGrid(columns,rows,size){
  if(invalidSpriteGridCount(columns) || invalidSpriteGridCount(rows) || !size)return true;
  const cols=Number(columns),lines=Number(rows);
  return cols*lines>128 || cols>size.width || lines>size.height;
}

export function invalidSpriteFrameRange(first,last,count){
  const valid=value=>value!=null && String(value).trim()!=='' && Number.isInteger(Number(value)) && Number(value)>=1 && Number(value)<=count;
  return !Number.isInteger(count) || count<1 || !valid(first) || !valid(last) || Number(first)>Number(last);
}

export function spriteFrameFieldIssues(row){
  const number=key=>row[key]==null || String(row[key]).trim()==='' ? NaN : Number(row[key]);
  const values=Object.fromEntries(['x','y','width','height','anchorX','anchorY'].map(key=>[key,number(key)]));
  const issues={};
  for(const key of ['x','y'])if(!Number.isInteger(values[key]) || Math.abs(values[key])>16777216)issues[key]='좌표는 허용 범위의 정수여야 합니다.';
  for(const key of ['width','height'])if(!Number.isInteger(values[key]) || values[key]<=0)issues[key]='크기는 양의 정수여야 합니다.';
  for(const [key,dimension] of [['anchorX','width'],['anchorY','height']])if(!Number.isFinite(values[key]) || values[key]<0 || (!issues[dimension] && values[key]>=values[dimension]))issues[key]='앵커는 프레임 크기 안에 있어야 합니다.';
  return issues;
}
export function spriteFrameIssue(row){return Object.values(spriteFrameFieldIssues(row))[0] || '';}
