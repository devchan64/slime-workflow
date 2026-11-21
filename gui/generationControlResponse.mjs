// A successful HTTP response alone does not establish that the selected job
// was resumed or that its cancellation was accepted.
export function validateGenerationControlResponse(command, id, response) {
  if (!response || typeof response !== 'object' || Array.isArray(response) ||
      ('id' in response && response.id !== id)) return false;
  if (command === 'cancel') return response.cancel_requested === true;
  if (command === 'resume') return response.id === id && response.status === 'queued';
  return false;
}
