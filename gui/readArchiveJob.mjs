export async function readArchiveJob(command, service, id, options = {}) {
  const history = await command(service, "history", {}, options);
  if(!Array.isArray(history?.records) || history.records.some(record=>!record || typeof record!=="object" || typeof record.id!=="string"))
    throw new Error("보관 이력 응답 형식을 확인할 수 없습니다. 다시 조회하세요.");
  return history.records.find(record => record.id === id) || {};
}
