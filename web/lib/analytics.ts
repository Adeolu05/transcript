/**
 * Anonymous product analytics — fire-and-forget event tracking.
 * No PII, no raw URLs. Session ID stored in localStorage.
 */

import { PUBLIC_API_BASE } from './publicApiBase';

const SESSION_KEY = 'tf_session_id';

function uuid(): string {
    return crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36);
}

/** Read or create a persistent anonymous session ID. */
export function getSessionId(): string {
    if (typeof window === 'undefined') return 'ssr';
    let id = localStorage.getItem(SESSION_KEY);
    if (!id) {
        id = uuid();
        localStorage.setItem(SESSION_KEY, id);
    }
    return id;
}

/**
 * Fire-and-forget event tracking.
 * Never blocks UI — failures are silently ignored.
 */
export function trackEvent(
    eventName: string,
    props?: Record<string, string | number | boolean | null>,
): void {
    try {
        const body = JSON.stringify({
            event_name: eventName,
            session_id: getSessionId(),
            app_source: 'web',
            props: props ?? {},
        });

        // navigator.sendBeacon is faster & survives page unloads
        if (navigator.sendBeacon) {
            const blob = new Blob([body], { type: 'application/json' });
            navigator.sendBeacon(`${PUBLIC_API_BASE}/api/v1/events`, blob);
        } else {
            fetch(`${PUBLIC_API_BASE}/api/v1/events`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body,
                keepalive: true,
            }).catch(() => { });
        }
    } catch {
        // Never throw — analytics must not break the app
    }
}
