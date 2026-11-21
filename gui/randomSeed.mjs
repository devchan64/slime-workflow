export function randomSeed(max, source=globalThis.crypto) {
  if (!Number.isInteger(max) || max<0 || max>0xffffffff) throw new RangeError('시드 범위를 확인할 수 없습니다.');
  const size=max+1, limit=Math.floor(0x100000000/size)*size, data=new Uint32Array(1);
  do { source.getRandomValues(data); } while (data[0]>=limit);
  return data[0]%size;
}
