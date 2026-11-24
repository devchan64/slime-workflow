import {validSnapshotPage} from "./snapshotPageValidation.mjs";

export function validKeyframeCatalogPage(result,cursor){
  return typeof result?.note==="string" && validSnapshotPage(result,cursor,{field:"items",limit:20,validItem:item=>/^[a-f0-9]{32}$/.test(item.id) && typeof item.tag==="string" && Number.isSafeInteger(item.source_frame) && item.source_frame>0});
}
