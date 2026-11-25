/** 같은 이름의 선택지만 ID를 덧붙여 구별한다. */
export function choiceLabels(choices){
  const counts=new Map();
  for(const [name] of choices)counts.set(name,(counts.get(name) || 0)+1);
  const used=new Set();
  return choices.map(([name,id])=>{
    const base=counts.get(name)>1 ? `${name} · ${id}` : name;
    let label=base,number=2;
    while(used.has(label))label=`${base} · ${number++}`;
    used.add(label);
    return [id,label];
  });
}
