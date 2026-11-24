import {validSnapshotPage} from "./snapshotPageValidation.mjs";

export function validExpressionCatalogPage(result,cursor){
  return validSnapshotPage(result,cursor,{field:"records",limit:20,validItem:row=>typeof row.label==="string"});
}
export const firstExpressionPage=Object.freeze({});
export function expressionCursorForQuery(pagination,query){
  return pagination.query===query ? pagination.cursor : firstExpressionPage;
}
export function resetExpressionQuery(pagination,query){
  return pagination.query===query ? pagination : {query,cursor:firstExpressionPage};
}
