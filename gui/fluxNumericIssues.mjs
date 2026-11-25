const integerIn=(value,min,max)=>value!=='' && value!=null && Number.isInteger(Number(value)) && Number(value)>=min && Number(value)<=max;
export function fluxNumericIssues(form,service){
  const max=service==='flux-character' ? 2048 : 1664;
  const size=value=>integerIn(value,256,max) && Number(value)%16===0;
  return {
    width:!size(form.width) ? `너비는 256~${max}의 16배수로 입력하세요.` : '',
    height:!size(form.height) ? `높이는 256~${max}의 16배수로 입력하세요.` : '',
    steps:service==='flux-character' && !integerIn(form.steps,1,50) ? '생성 스텝은 1~50의 정수로 입력하세요.' : '',
    seed:!integerIn(form.seed,0,4294967295) ? '시드는 0부터 4,294,967,295까지의 정수로 입력하세요.' : ''
  };
}
