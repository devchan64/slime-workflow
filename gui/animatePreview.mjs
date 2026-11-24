export async function prepareAnimatePreview({reference,motion,prompt,frames,steps,seed,lora,signal,materialize,referencePng,videoData,previewHandoff}){
  const check=()=>{if(signal.aborted)throw new DOMException('검토 중단','AbortError');};
  check();
  const image=await materialize(reference,'image/png',signal);check();
  const video=await materialize(motion,'video/mp4',signal);check();
  const images=[await referencePng(image)];check();
  const driving_video=await videoData(video);check();
  const request={action:'generate',images,driving_video,prompt,frames,steps,seed,width:832,height:480,lora_mode:lora};
  await previewHandoff(request,{signal});check();
  return request;
}
