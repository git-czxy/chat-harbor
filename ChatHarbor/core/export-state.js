export const EXPORT_STATE_SCHEMA = 'chatharbor-export-state-v1';

export function createExportState(identity) {
  return { schemaVersion: EXPORT_STATE_SCHEMA, identity, currentObservedVersion: null, versionStatus: 'unknown', exportedVersions: [], lastSuccessfulExport: null, legacyExported: false };
}

export function deriveExportStatus(state) {
  if (!state.exportedVersions.length) return 'never_exported';
  if (state.currentObservedVersion == null) return 'unknown';
  return state.exportedVersions.some(item => item.contentVersion === state.currentObservedVersion) ? 'latest' : 'has_updates';
}

export function recordObservedVersion(state, version) {
  const next = { ...state, currentObservedVersion: version ?? null, versionStatus: version == null ? 'unknown' : 'known' };
  return { ...next, status: deriveExportStatus(next) };
}

export function recordSuccessfulExport(state, artifact) {
  const exportedVersions = [...state.exportedVersions.filter(item => item.contentVersion !== artifact.contentVersion), artifact];
  const next = { ...state, exportedVersions, lastSuccessfulExport: artifact.exportedAt };
  return { ...next, status: deriveExportStatus(next) };
}

export function migrateLegacyState(identity, legacy = {}) {
  const state = createExportState(identity);
  return { ...state, legacyExported: (legacy.exported || []).includes(identity), status: (legacy.exported || []).includes(identity) ? 'unknown' : 'never_exported' };
}
