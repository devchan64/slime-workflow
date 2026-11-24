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
  if(!example || typeof example.label!=="string" || typeof example.prompt!=="string" || !Number.isSafeInteger(example.frames) || example.frames<30 || example.frames>300 || !example.settings || typeof example.settings!=="object" || Array.isArray(example.settings) || !Array.isArray(example.references) || example.references.some(row=>!row || typeof row.name!=="string" || typeof row.data!=="string"))return false;
  const {keyframes,segment_frames,directions}=example.settings;
  if(Object.hasOwn(example.settings,"directions") && (!Array.isArray(directions) || !directions.length || directions.some(value=>typeof value!=="string" || !value) || new Set(directions).size!==directions.length))return false;
  for(const [field,min,max,integer] of [["steps",2,100,true],["seed",0,2147483647,true],["guidance_scale",0,10,false],["heading_degrees",-180,180,false],["openpose_scale_percent",10,100,false]]){
    if(Object.hasOwn(example.settings,field)){
      const value=example.settings[field];
      if(typeof value!=="number" || !Number.isFinite(value) || (integer && !Number.isSafeInteger(value)) || value<min || value>max)return false;
    }
  }
  for(const field of ["post_processing","remove_horizontal_motion","pose_include_hands","pose_include_face"])
    if(Object.hasOwn(example.settings,field) && typeof example.settings[field]!=="boolean")return false;
  if(Object.hasOwn(example.settings,"camera_elevation_degrees") && ![0,15,30].includes(example.settings.camera_elevation_degrees))return false;
  if(keyframes!=null && (!Array.isArray(keyframes) || keyframes.length && !validKeyframeBatchRequest(keyframes,example.frames)))return false;
  if(keyframes?.length && (example.settings.post_processing!==true || example.settings.remove_horizontal_motion===true))return false;
  if(segment_frames!=null && (!Array.isArray(segment_frames) || segment_frames.length<2 || segment_frames.length>10 || segment_frames.some(value=>!Number.isSafeInteger(value) || value<16 || value>300) || segment_frames.reduce((sum,value)=>sum+value,0)!==example.frames || example.prompt.split(/\r?\n/).filter(line=>line.trim()).length!==segment_frames.length))return false;
  return true;
}
