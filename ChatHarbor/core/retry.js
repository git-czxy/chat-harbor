export function statusOf(error) {
  return Number.isInteger(error?.status) ? error.status : null;
}

export function isRetryableError(error) {
  const status = statusOf(error);
  return status === null || status >= 500;
}

export class RetryCancelledError extends Error {
  constructor() { super('Retry cancelled'); this.name = 'RetryCancelledError'; }
}

export async function retryOperation(operation, {
  maxAttempts = 3,
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms)),
  random = Math.random,
  isCancelRequested = () => false,
  refreshAuth = null,
  onRetry = () => {}
} = {}) {
  let refreshedAuth = false;
  let lastError;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    if (isCancelRequested()) throw new RetryCancelledError();
    try { return await operation(); }
    catch (error) {
      lastError = error;
      const status = statusOf(error);
      if ((status === 401 || status === 403) && attempt < maxAttempts && !refreshedAuth && typeof refreshAuth === 'function') {
        refreshedAuth = true;
        if (await refreshAuth()) {
          if (isCancelRequested()) throw new RetryCancelledError();
          continue;
        }
        throw error;
      }
      if (!isRetryableError(error) || attempt === maxAttempts) throw error;
      const delay = (2 ** attempt) * 1000 + Math.floor(random() * 501);
      onRetry({ attempt, delay, error });
      await sleep(delay);
      if (isCancelRequested()) throw new RetryCancelledError();
    }
  }
  throw lastError;
}
