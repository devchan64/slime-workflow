export function linkedSpriteSheet(search){
  const params=new URLSearchParams(search);
  const path=params.get('sprite_path') || '',action=params.get('action') || '';
  const source=params.get('sprite_source') ?? 'assets';
  if((path || action) && !['assets','baseline'].includes(source))return {error:'지원하지 않는 링크 원본입니다.'};
  if(path)return {source,path};
  if(!action)return {};
  if(!action.startsWith('asset:') || action.length===6)return {error:'지원하지 않는 애니메이션 링크입니다.'};
  return {source:'assets',animation:action.slice(6)};
}
export function findLinkedSprite(items,animation){
  const matches=items.filter(item=>Array.isArray(item?.animationIds) && item.animationIds.includes(animation));
  return matches.length===1 && typeof matches[0].path==='string' && matches[0].path ? matches[0].path : null;
}
