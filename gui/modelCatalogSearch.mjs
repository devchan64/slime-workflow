export function searchCatalog(components, query) {
  const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return components.filter(({declaration: item, declared_version: version, alternate_installations: alternates}) => {
    const text = [item.id, item.label, item.kind, item.path, item.source || '', item.revision || '', item.usage_note || '',
      version?.id || '', ...(item.services || []), ...(alternates || []).map(alt => alt.path)].join(' ').toLocaleLowerCase();
    return terms.every(term => text.includes(term));
  });
}

export function installationJobs(jobs, target) {
  if (!Array.isArray(jobs) || !target) return [];
  return jobs.filter(job => job && job.model === target);
}

export function relatedActivity(activity, services) {
  const names = new Set(services || []);
  const matches = job => names.has(job.source_service || job.service);
  return {
    queued: (activity?.queue?.jobs || []).filter(matches),
    reservations: (activity?.reservations?.records || []).filter(matches)
  };
}

export function sortCatalog(components, order) {
  if (order !== 'allocated') return components;
  const size = item => item.presence?.local_present === false
    ? item.alternate_installations?.find(alt => alt.local_present && alt.storage_observation)?.storage_observation?.allocated_bytes
    : item.storage_observation?.allocated_bytes;
  return [...components].sort((a, b) => {
    const av = size(a), bv = size(b);
    const aKnown = Number.isFinite(av), bKnown = Number.isFinite(bv);
    if (aKnown !== bKnown) return aKnown ? -1 : 1;
    return aKnown ? bv - av : 0;
  });
}
