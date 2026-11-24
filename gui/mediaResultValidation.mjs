export function validMediaResultDetails(job,kind,service) {
  if (job.note!=null && typeof job.note!=="string") return false;
  if (job.result_status==="available" && ["image","flux","character","video"].includes(kind)) {
    const field=kind==="video" && service!=="dwpose" ? "video" : "image";
    if (typeof job[field]!=="string" || !job[field]) return false;
  }
  if (kind!=="audio") return true;
  if (job.tracks!=null && (!Array.isArray(job.tracks) || job.tracks.some(track=>!track || typeof track.label!=="string" || !track.label.trim() || typeof track.wav!=="string" || !track.wav.trim() || (track.mp3!=null && typeof track.mp3!=="string")) || new Set(job.tracks.map(track=>track.wav)).size!==job.tracks.length)) return false;
  return !(job.result_status==="available" && job.file_observation!=="unavailable" && !job.tracks?.length && (typeof job.audio!=="string" || !job.audio));
}

export function mediaResultPendingMessage(job){
  if(job?.result_status!=="not_ready" || job.file_observation==="unavailable")return "";
  if(["queued","running"].includes(job.status))return "결과 파일은 아직 준비되지 않았습니다. 작업 진행 상태를 확인하세요.";
  if(["failed","cancelled","canceled","paused"].includes(job.status))return "결과 파일을 표시할 수 없습니다. 작업 상태와 이력을 확인하세요.";
  return "결과 파일이 아직 준비되지 않았습니다. 작업 상태와 이력을 확인하세요.";
}

export function mediaResultErrorMessage(problem,fallback){
  return typeof problem?.message==="string" && problem.message.trim() ? problem.message : fallback;
}
