// Dev-only logger. In production builds (NODE_ENV === "production") all logs
// are silently swallowed so we never expose stack traces or internals to users.
// If you wire up Sentry later, replace `console.error` with `Sentry.captureException(err)`.
const IS_DEV = process.env.NODE_ENV !== "production";

export function logError(...args) {
  if (IS_DEV) {
    // eslint-disable-next-line no-console
    console.error(...args);
  }
}

export function logWarn(...args) {
  if (IS_DEV) {
    // eslint-disable-next-line no-console
    console.warn(...args);
  }
}
