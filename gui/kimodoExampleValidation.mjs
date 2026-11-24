import {validKeyframeBatchRequest} from "./keyframeBatchValidation.mjs";

export function validKimodoExampleList(rows){
  if(!Array.isArray(rows))return false;
  const ids=new Set();
  return rows.every(row=>{
    if(!row || typeof row.id!=="string" || !row.id || ids.has(row.id) || typeof row.label!=="string" || typeof row.prompt!=="string")return false;
    ids.add(row.id);return true;
  });
}

export function validKimodoExample(example){
  if(!example || typeof example.label!=="string" || typeof example.prompt!=="string" || !Number.isSafeInteger(example.frames) || !example.settings || typeof example.settings!=="object" || Array.isArray(example.settings) || !Array.isArray(example.references) || example.references.some(row=>!row || typeof row.name!=="string" || typeof row.data!=="string"))return false;
  const {keyframes,segment_frames}=example.settings;
  if(keyframes!=null && (!Array.isArray(keyframes) || keyframes.length && !validKeyframeBatchRequest(keyframes,example.frames)))return false;
  if(segment_frames!=null && (!Array.isArray(segment_frames) || segment_frames.some(value=>!Number.isSafeInteger(value))))return false;
  return true;
}
