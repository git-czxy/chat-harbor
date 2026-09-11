export const EXPORT_STATE_SCHEMA = 'chatharbor-export-state-v1';

export function createExportState(identity) {
  return { schemaVersion: EXPORT_STATE_SCHEMA, identity, currentObservedVersion: null, versionStatus: 'unknown', exportedVersions: [], lastSuccessfulExport: null, legacyExported: false, status: 'never_exported' };
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
  const existing = state.exportedVersions.find(item => item.contentVersion === artifact.contentVersion);
  const merged = existing ? { ...existing, ...artifact, representations: [...new Set([...(existing.representations || []), ...(artifact.representations || [])])], artifactRefs: [...new Set([...(existing.artifactRefs || []), ...(artifact.artifactRefs || [])])] } : artifact;
  const exportedVersions = existing ? state.exportedVersions.map(item => item.contentVersion === artifact.contentVersion ? merged : item) : [...state.exportedVersions, merged];
  const next = { ...state, exportedVersions, lastSuccessfulExport: artifact.exportedAt };
  return { ...next, status: deriveExportStatus(next) };
}

export function migrateLegacyState(identity, legacy = {}) {
  const state = createExportState(identity);
  return { ...state, legacyExported: (legacy.exported || []).includes(identity), status: (legacy.exported || []).includes(identity) ? 'unknown' : 'never_exported' };
}

export function recoverArtifact(state, artifact) {
  if (!artifact?.identity || artifact.identity !== state.identity || artifact.contentVersion == null) return state;
  return recordSuccessfulExport(state, artifact);
}
