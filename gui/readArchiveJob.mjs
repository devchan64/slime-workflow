export async function readArchiveJob(command, service, id) {
  const history = await command(service, "history", {});
  return history.records.find(record => record.id === id) || {};
}
