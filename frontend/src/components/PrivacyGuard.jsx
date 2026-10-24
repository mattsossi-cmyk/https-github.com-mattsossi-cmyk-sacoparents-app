import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * PrivacyGuard — SA CoParents
 * Put in: frontend/src/components/PrivacyGuard.jsx
 *
 * Stops analytics / tracking tools from recording visits to sensitive pages.
 * Works with Google Analytics (gtag), the Facebook/Meta Pixel (fbq) and PostHog,
 * whichever ones the site has. If the site has none, it does nothing.
 *
 * Add ONE line in frontend/src/App.js, inside <BrowserRouter> and above <Routes>:
 *   <PrivacyGuard />
 */

// Any page whose address starts with one of these is never tracked.
export const SENSITIVE_PATHS = ['/self-journey', '/start-with-safety', '/safety-first'];

export function isSensitivePath(pathname) {
  return SENSITIVE_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/'));
}

// Google Analytics IDs look like "G-XXXXXXX". This reads them from the page
// so you don't have to type them in.
function googleAnalyticsIds() {
  const ids = new Set(window.__SACP_GA_IDS || []);
  (window.dataLayer || []).forEach((entry) => {
    if (entry && entry[0] === 'config' && typeof entry[1] === 'string') ids.add(entry[1]);
  });
  return [...ids];
}

function setTracking(allowed) {
  // Google Analytics: official "disable" switch, checked before every hit
  googleAnalyticsIds().forEach((id) => {
    window[`ga-disable-${id}`] = !allowed;
  });

  // Facebook / Meta Pixel
  if (typeof window.fbq === 'function') {
    window.fbq('consent', allowed ? 'grant' : 'revoke');
  }

  // PostHog
  const ph = window.posthog;
  if (ph && typeof ph.opt_out_capturing === 'function') {
    if (!allowed) ph.opt_out_capturing();
    else if (ph.has_opted_out_capturing && ph.has_opted_out_capturing()) {
      ph.opt_in_capturing({ captureEventName: null });
    }
  }
}

export default function PrivacyGuard() {
  const { pathname } = useLocation();

  useEffect(() => {
    setTracking(!isSensitivePath(pathname));
  }, [pathname]);

  return null;
}
