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

export function spriteOutputSizeIssues(rows,columns,gif=false){
  if(!rows.length || invalidSpriteGridCount(columns) || rows.some(spriteFrameIssue))return [];
  const count=Number(columns);
  let width=0,height=0;
  for(let i=0;i<rows.length;i+=count){
    const row=rows.slice(i,i+count);
    width=Math.max(width,row.reduce((sum,frame)=>sum+Number(frame.width),0));
    height+=Math.max(...row.map(frame=>Number(frame.height)));
  }
  const issues=[];
  if(width*height>16_777_216)issues.push(gif ? 'GIF용 출력 시트는 16,777,216픽셀 이하여야 합니다. 프레임 크기나 선택 범위를 줄이세요.' : '출력 시트는 16,777,216픽셀 이하여야 합니다. 프레임 크기나 출력 열 수를 조정하세요.');
  if(gif){
    const canvasWidth=Math.ceil(Math.max(...rows.map(frame=>Number(frame.anchorX))))+Math.ceil(Math.max(...rows.map(frame=>Number(frame.width)-Number(frame.anchorX))));
    const canvasHeight=Math.ceil(Math.max(...rows.map(frame=>Number(frame.anchorY))))+Math.ceil(Math.max(...rows.map(frame=>Number(frame.height)-Number(frame.anchorY))));
    if(canvasWidth*canvasHeight*rows.length>64_000_000)issues.push('GIF 전체 프레임 크기가 허용 범위를 초과합니다. 프레임 크기나 선택 범위를 줄이세요.');
  }
  return issues;
}
