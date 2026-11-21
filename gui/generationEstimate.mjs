// Accept only complete, finite service estimates; never infer missing values.
const zonedTime = value => typeof value === "string" && /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && !Number.isNaN(Date.parse(value));
export function validGenerationEstimate(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  if (typeof value.basis !== 'string' || typeof value.scope !== 'string' ||
      !zonedTime(value.updated_at) ||
      !Number.isSafeInteger(value.sample_count) || value.sample_count < 0) return false;
  for (const key of ['remaining','total_seconds','estimated_progress']) {
    if (value[key] !== null && (!Number.isFinite(value[key]) || value[key] < 0)) return false;
  }
  if (value.estimated_progress !== null && value.estimated_progress >= 100) return false;
  if (value.total_seconds !== null && value.total_seconds <= 0) return false;
  return value.completion === null || zonedTime(value.completion);
}
