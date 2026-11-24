import {validSnapshotPage} from "./snapshotPageValidation.mjs";

export function validExpressionCatalogPage(result,cursor){
  return validSnapshotPage(result,cursor,{field:"records",limit:20,validItem:row=>typeof row.label==="string"});
}
