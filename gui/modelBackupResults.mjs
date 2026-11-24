export function modelBackupPage(files, filter, page, pageSize = 100) {
  const counts = Object.create(null);
  for (const file of files) counts[file.status] = (counts[file.status] || 0) + 1;
  const filtered = files.filter(file => filter === 'all' || file.status === filter);
  const lastPage = Math.max(0, Math.ceil(filtered.length / pageSize) - 1);
  const currentPage = Math.min(Math.max(0, page), lastPage);
  return {counts, total: filtered.length, page: currentPage,
          files: filtered.slice(currentPage * pageSize, (currentPage + 1) * pageSize)};
}
