// Generation-specific readiness includes runtime requirements when provided.
export function generationReady(status){
  return Boolean(status?.generation_ready ?? status?.ready);
}
