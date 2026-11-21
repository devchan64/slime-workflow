// All required videos must be inspected before their shared output limit is known.
export function videoFrameLimit(keys, info) {
  if (!keys.length) return null;
  const limits=keys.map(key=>info[key]?.maximum_frames);
  return limits.every(value=>Number.isInteger(value) && value>=5) ? Math.min(...limits) : null;
}
