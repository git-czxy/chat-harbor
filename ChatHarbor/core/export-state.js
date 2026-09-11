export const EXPORT_STATE_SCHEMA = 'chatharbor-export-state-v1';

export function createExportState(identity) {
  return { schemaVersion: EXPORT_STATE_SCHEMA, identity, currentObservedVersion: null, versionStatus: 'unknown', exportedVersions: [], lastSuccessfulExport: null, legacyExported: false, legacyPending: false, status: 'never_exported' };
}

export function deriveExportStatus(state) {
  if (!state.exportedVersions.length) return state.legacyExported ? 'unknown' : 'never_exported';
  if (state.currentObservedVersion == null) return 'unknown';
  return state.exportedVersions.some(item => item.contentVersion === state.currentObservedVersion) ? 'latest' : 'has_updates';
}

export function recordObservedVersion(state, version) {
  const next = { ...state, currentObservedVersion: version ?? null, versionStatus: version == null ? 'unknown' : 'known' };
  return { ...next, status: deriveExportStatus(next) };
}

export function recordSuccessfulExport(state, artifact) {
  const comparable = artifact.contentVersion != null;
  const existing = state.exportedVersions.find(item => comparable ? item.contentVersion === artifact.contentVersion : item.artifactId && item.artifactId === artifact.artifactId);
  const merged = existing ? { ...existing, ...artifact, representations: [...new Set([...(existing.representations || []), ...(artifact.representations || [])])], artifactRefs: [...new Set([...(existing.artifactRefs || []), ...(artifact.artifactRefs || [])])] } : artifact;
  const exportedVersions = existing ? state.exportedVersions.map(item => item.contentVersion === artifact.contentVersion ? merged : item) : [...state.exportedVersions, merged];
  const next = { ...state, exportedVersions, lastSuccessfulExport: artifact.exportedAt };
  return { ...next, status: deriveExportStatus(next) };
}

export function migrateLegacyState(identity, legacy = {}) {
  const state = createExportState(identity);
  const legacyExported = (legacy.exported || []).includes(identity);
  const legacyPending = (legacy.pending || []).includes(identity);
  return { ...state, legacyExported, legacyPending, status: legacyExported ? 'unknown' : 'never_exported' };
}

export function recoverArtifact(state, artifact) {
  if (!artifact?.identity || artifact.identity !== state.identity || !artifact.artifactId) return state;
  return recordSuccessfulExport(state, artifact);
}
