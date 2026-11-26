export function validRef2vaVideoFile(file){
  return Boolean(file && file.size>0 && file.size<=27*1024*1024 &&
    (file.type === 'video/mp4' || (!file.type && /\.mp4$/i.test(file.name || ''))));
}
