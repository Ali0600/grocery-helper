import { isRetryable } from '../api';

// Build an Error with a specific `name` (e.g. the AbortController's "AbortError" on timeout).
function named(name: string, message = ''): Error {
  const e = new Error(message);
  e.name = name;
  return e;
}

describe('isRetryable', () => {
  it('retries a timeout (AbortError) and network-level failures', () => {
    expect(isRetryable(named('AbortError'))).toBe(true);
    expect(isRetryable(new TypeError('Network request failed'))).toBe(true);
    expect(isRetryable(new Error('Failed to fetch'))).toBe(true);
  });

  it('retries 5xx (a waking / redeploying backend) but not 4xx (a real client error)', () => {
    expect(isRetryable(new Error('API 500'))).toBe(true);
    expect(isRetryable(new Error('API 502'))).toBe(true);
    expect(isRetryable(new Error('API 503'))).toBe(true);
    expect(isRetryable(new Error('API 404'))).toBe(false);
    expect(isRetryable(new Error('API 403'))).toBe(false);
    expect(isRetryable(new Error('API 400'))).toBe(false);
  });

  it('does not retry a non-Error value', () => {
    expect(isRetryable('nope')).toBe(false);
    expect(isRetryable(null)).toBe(false);
    expect(isRetryable(undefined)).toBe(false);
  });
});
