import * as Sentry from '@sentry/browser';

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
    Sentry.init({
        dsn,
        sendDefaultPii: false,
        tracesSampleRate: 0.1,

        beforeSend(event) {
            // Strip request URLs to avoid storing raw video links
            if (event.request) {
                delete event.request.url;
                delete event.request.query_string;
                delete event.request.data;
            }
            return event;
        },
    });
}
