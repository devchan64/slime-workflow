export function qwenArchiveUrl(href,job){
  const url=new URL(href);
  if(job)url.searchParams.set('job',job);
  else url.searchParams.delete('job');
  return url;
}
