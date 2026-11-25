/** 같은 이름의 선택지만 ID를 덧붙여 구별한다. */
export function choiceLabels(choices){
  const counts=new Map();
  for(const [name] of choices)counts.set(name,(counts.get(name) || 0)+1);
  return choices.map(([name,id])=>[id,counts.get(name)>1 ? `${name} · ${id}` : name]);
}
