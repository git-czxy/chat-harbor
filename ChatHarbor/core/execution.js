export function createExecutionController(targets, execute, { onUpdate = () => {} } = {}) {
  const state = { total: targets.length, currentIndex: 0, currentIdentity: null, completed: 0, success: 0, skipped: 0, failed: 0, failures: [], status: 'idle', cancelRequested: false };
  const snapshot = () => ({ ...state, failures: [...state.failures], remaining: state.total - state.completed });
  const update = () => onUpdate(snapshot());
  return {
    snapshot,
    requestCancel() { if (state.status === 'running') { state.cancelRequested = true; state.status = 'cancelling'; update(); } },
    async run() {
      if (state.status !== 'idle') throw new Error('Execution already started');
      state.status = 'running'; update();
      for (let index = 0; index < targets.length; index++) {
        if (state.cancelRequested) break;
        const target = targets[index]; state.currentIndex = index + 1; state.currentIdentity = target.identity; update();
        try { await execute(target); state.success++; }
        catch (error) { state.failed++; state.failures.push({ identity: target.identity, error: String(error?.message || error) }); }
        state.completed++; update();
      }
      state.currentIdentity = null;
      state.status = state.cancelRequested ? 'cancelled' : 'completed'; update();
      return snapshot();
    }
  };
}
