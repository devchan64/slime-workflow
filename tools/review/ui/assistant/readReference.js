export default function readReference(file){
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(reader.result.split(",")[1]);
    reader.onerror=()=>reject(new Error("참조 파일을 읽을 수 없습니다."));
    reader.readAsDataURL(file);
  });
}
