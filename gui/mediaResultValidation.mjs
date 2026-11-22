export function validMediaResultDetails(job,kind,service) {
  if (job.note!=null && typeof job.note!=="string") return false;
  if (job.result_status==="available" && ["image","flux","character","video"].includes(kind)) {
    const field=kind==="video" && service!=="dwpose" ? "video" : "image";
    if (typeof job[field]!=="string" || !job[field]) return false;
  }
  if (kind!=="audio") return true;
  if (job.tracks!=null && (!Array.isArray(job.tracks) || job.tracks.some(track=>!track || typeof track.label!=="string" || typeof track.wav!=="string" || !track.wav || (track.mp3!=null && typeof track.mp3!=="string")))) return false;
  return !(job.result_status==="available" && job.file_observation!=="unavailable" && !job.tracks?.length && (typeof job.audio!=="string" || !job.audio));
}
