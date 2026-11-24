export function validFluxProfile(value){
  if(!value || typeof value!=="object" || Array.isArray(value) || typeof value.label!=="string" || !value.label.trim() || typeof value.prompt!=="string" ||
     !Number.isInteger(value.width) || value.width<=0 || !Number.isInteger(value.height) || value.height<=0 ||
     !Number.isInteger(value.minimum) || value.minimum<0 || value.minimum>3 ||
     ["description","rolePrompt","subject"].some(key=>value[key]!=null && typeof value[key]!=="string"))return false;
  if(["guides","stages","expressions"].some(key=>value[key]!=null && (!Array.isArray(value[key]) || value[key].some(item=>!item || typeof item!=="object" || Array.isArray(item) || typeof item.id!=="string" || !item.id.trim() || typeof item.label!=="string" || (key==="expressions" && typeof item.text!=="string")))))return false;
  return value.layouts==null || (Array.isArray(value.layouts) && value.layouts.every(item=>typeof item==="string"));
}
