export function validSessionViewPage(page,session,historyPage,limit){
  if(!page || page.id!==session || !Array.isArray(page.messages) || page.messages.length>limit ||
    !Number.isInteger(page.message_count) || page.message_count<0 ||
    page.offset!==(historyPage?.offset || 0) || page.offset+page.messages.length>page.message_count ||
    !/^[a-f0-9]{64}$/.test(page.snapshot || "") || (historyPage?.snapshot && page.snapshot!==historyPage.snapshot))return false;
  const next=page.offset+page.messages.length;
  if(page.next_offset===null ? next!==page.message_count :
    !Number.isInteger(page.next_offset) || page.messages.length===0 || page.next_offset!==next || next>=page.message_count)return false;
  return page.messages.every(message=>{
    if(!message || typeof message.text!=="string" ||
      (message.job!=null && (typeof message.job!=="object" || Array.isArray(message.job))))return false;
    const activity=message.job?.tool_activity;
    if(activity!=null && (typeof activity!=="object" || Array.isArray(activity)))return false;
    const events=activity?.events;
    if(events!=null && (!Array.isArray(events) || events.some(event=>!event || typeof event!=="object" || Array.isArray(event) ||
      [event.type,event.name,event.call_id,event.timestamp,event.target,event.output].some(value=>value!=null && typeof value!=="string"))))return false;
    const history=activity?.source_history_page;
    if(history!=null && (!history || typeof history.service!=="string" || !Number.isInteger(history.total) ||
      !Array.isArray(history.rows) || history.rows.some(row=>!row || typeof row.id!=="string" || typeof row.status!=="string")))return false;
    const table=activity?.history_table;
    if(table!=null && (!table || typeof table.title!=="string" || typeof table.summary!=="string" ||
      !Array.isArray(table.columns) || table.columns.some(column=>typeof column!=="string") ||
      !Array.isArray(table.rows) || table.rows.some(row=>!Array.isArray(row) || row.some(value=>typeof value!=="string"))))return false;
    return true;
  });
}
