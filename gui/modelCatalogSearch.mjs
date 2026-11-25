import {validBackupJob} from './modelBackupResults.mjs';

export function validCatalogHistory(value) {
  return Boolean(value && Array.isArray(value.records) && value.records.every(record=>record && typeof record==='object' && !Array.isArray(record) &&
    typeof record.job_id==='string' && ['model','operation','status','started_at'].every(key=>record[key]==null || typeof record[key]==='string')));
}
export function validCatalogVerification(value,jobId,model) {
  return Boolean(validBackupJob(value,jobId) && value.model===model && (value.target==null || typeof value.target==='string'));
}

export function validCatalogOverview(value) {
  const object=item=>item!==null && typeof item==='object' && !Array.isArray(item);
  const objects=items=>Array.isArray(items) && items.every(object);
  const optionalObjects=items=>items==null || objects(items);
  const optionalText=(item,keys)=>keys.every(key=>item[key]==null || typeof item[key]==='string');
  const validInstall=install=>install==null || (object(install) && optionalObjects(install.declared_sources) && (install.declared_file_count==null || Number.isFinite(install.declared_file_count)));
  if(!object(value) || !objects(value.components) || !objects(value.unclassified) || !optionalObjects(value.unclassified_nested))return false;
  if(!optionalText(value,['note','backup_error']) || value.unclassified.some(item=>typeof item.name!=='string'))return false;
  if(value.storage_survey!=null && (!object(value.storage_survey) || !optionalText(value.storage_survey,['finished_at'])))return false;
  if(value.activity!=null && (!object(value.activity) || (value.activity.queue!=null && (!object(value.activity.queue) || !optionalObjects(value.activity.queue.jobs))) || (value.activity.reservations!=null && (!object(value.activity.reservations) || !optionalObjects(value.activity.reservations.records)))))return false;
  if(value.activity?.queue?.status==='available' && !objects(value.activity.queue.jobs))return false;
  if(value.activity?.reservations?.status==='available' && !objects(value.activity.reservations.records))return false;
  if(value.unclassified_nested?.some(item=>typeof item.path!=='string' || !object(item.storage_observation) || !Number.isFinite(item.storage_observation.files)))return false;
  return value.components.every(component=>{
    const item=component.declaration;
    return object(item) && ['id','label','kind','path'].every(key=>typeof item[key]==='string') && optionalText(item,['source','revision','usage_note']) && Array.isArray(item.services) && item.services.every(service=>typeof service==='string') &&
      (item.optional_services==null || (Array.isArray(item.optional_services) && item.optional_services.every(service=>typeof service==='string'))) &&
      (component.alternate_installations===undefined || objects(component.alternate_installations)) && optionalObjects(component.observed_links) &&
      (component.declared_version==null || (object(component.declared_version) && optionalText(component.declared_version,['id']))) &&
      validInstall(component.installation_metadata) && (component.alternate_installations || []).every(alt=>optionalText(alt,['path','backup_target']) && validInstall(alt.installation_metadata)) &&
      (component.observed_links || []).every(link=>optionalText(link,['path','resolved']));
  });
}

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
