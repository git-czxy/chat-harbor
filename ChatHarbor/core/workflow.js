export function buildExportConfirmation({ range, count, strategy, batchCount, skipLatest }) {
  return { range, count, strategy, batchCount, skipLatest: Boolean(skipLatest) };
}

export function preserveSelection(selected, filteredIds) {
  return new Set([...selected].filter(id => id != null));
}

export function exportStatusFor({ priorExport = false, currentVersion = null, exportedVersions = [] }) {
  if (!priorExport && !exportedVersions.length) return 'never_exported';
  if (currentVersion == null) return 'unknown';
  if (exportedVersions.some(version => version === currentVersion)) return 'latest';
  return exportedVersions.some(version => version == null) ? 'unknown' : 'has_updates';
}
