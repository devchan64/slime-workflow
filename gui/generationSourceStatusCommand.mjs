export function generationSourceStatusCommand(service) {
  if (service.startsWith('flux-')) return 'hermes-flux-source-status';
  if (service === 'minimax-h3-image') return 'hermes-image-source-status';
  if (service === 'music-heartmula' || service === 'sfx-dasheng-audiogen') return 'hermes-audio-source-status';
  return 'hermes-video-source-status';
}
