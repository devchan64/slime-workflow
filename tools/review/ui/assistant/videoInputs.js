export async function referencePng(file){
  const image=await createImageBitmap(file);
  try{
    const canvas=document.createElement("canvas");
    canvas.width=832;canvas.height=480;
    const ctx=canvas.getContext("2d");
    ctx.fillStyle="white";ctx.fillRect(0,0,832,480);
    const scale=Math.min(832/image.width,480/image.height);
    const w=Math.round(image.width*scale),h=Math.round(image.height*scale);
    ctx.drawImage(image,Math.floor((832-w)/2),Math.floor((480-h)/2),w,h);
    return canvas.toDataURL("image/png").split(",")[1];
  }finally{image.close();}
}
export function videoData(file){
  if(file.size>32*1024*1024)throw new Error("MP4당 최대 크기는 32MiB입니다.");
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(reader.result.split(",")[1]);
    reader.onerror=()=>reject(new Error("영상을 읽을 수 없습니다."));
    reader.readAsDataURL(file);
  });
}
