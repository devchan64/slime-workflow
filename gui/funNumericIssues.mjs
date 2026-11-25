export function funNumericIssues(request,frameLimit,maxSeed){
  const rules={frames:[5,frameLimit,4,'프레임 수'],steps:[2,100,1,'스텝'],seed:[0,maxSeed,1,'시드'],flow_shift:[0.1,20,null,'Flow shift'],guidance_scale:[1,10,null,'Guidance scale'],switch_ratio:[0.1,0.9,null,'모델 전환 비율']};
  return Object.fromEntries(Object.entries(rules).map(([key,[min,max,step,label]])=>{
    const value=request[key],number=Number(value);
    const invalid=value==='' || value==null || !Number.isFinite(number) || number<min || number>max || (step!==null && (!Number.isInteger(number) || (number-min)%step!==0));
    return [key,invalid ? `${label}: ${min}~${max} ${step===4 ? '범위에서 4프레임 간격으로' : step===1 ? '범위의 정수로' : '범위로'} 입력하세요.` : ''];
  }));
}
