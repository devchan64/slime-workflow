// The gateway exposes reviewed resume for these services; audio and translation
// validate the same fingerprint on their regular resume command.
const reviewedServices = new Set([
  "kimodo", "dwpose", "wan22-animate2", "wan22-vace", "wan22-fun-control",
  "flux-image", "flux-character", "flux-mannequin", "flux-billboard", "flux-prop",
  "flux-vegetation", "flux-building", "flux-seamless",
]);
const fingerprintResumeServices = new Set(["music-heartmula", "sfx-dasheng-audiogen", "prompt-translation"]);

export function generationResumeCommand(service) {
  if (reviewedServices.has(service)) return "resume-reviewed";
  if (fingerprintResumeServices.has(service)) return "resume";
  return null;
}
