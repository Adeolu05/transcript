import type { Metadata } from "next";
import Link from "next/link";
import { CONTACT_EMAIL, SITE_URL } from "../../lib/site";

export const metadata: Metadata = {
  title: "Privacy",
  description: "How Transcript Flow handles data when you extract YouTube and Vimeo transcripts.",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen" style={{ background: "var(--bg)", color: "var(--text)" }}>
      <div className="mx-auto max-w-2xl px-6 py-16 md:py-24">
        <Link
          href="/"
          className="text-[10px] font-bold uppercase tracking-widest transition-opacity hover:opacity-70"
          style={{ color: "var(--muted)" }}
        >
          ← Home
        </Link>
        <h1 className="mt-10 text-3xl font-semibold tracking-tight md:text-4xl" style={{ color: "var(--text)" }}>
          Privacy
        </h1>
        <p className="mt-4 text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
          Last updated: July 2026. This page describes how we handle information in connection with{" "}
          {SITE_URL}. It is a plain-language summary and is not legal advice; have counsel review if
          you need a formal policy.
        </p>

        <div className="mt-12 space-y-8 text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              What we do
            </h2>
            <p className="mt-3">
              Transcript Flow lets you submit a public YouTube or Vimeo URL to generate a transcript
              file (for example TXT, PDF, DOCX, SRT, or VTT). You do not need an account to use the web app.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              What you send us
            </h2>
            <p className="mt-3">
              When you use the service, our systems process the link you provide and communicate with
              YouTube, Vimeo, or related services as needed to obtain captions or transcripts. We do
              not require you to log in on the website for basic use.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Temporary files
            </h2>
            <p className="mt-3">
              Generated download files (and a short plain-text copy used to convert formats) are stored
              on our servers for a limited time so you can download them. They are designed to expire
              and be deleted automatically—typically within about one hour (exact TTL may vary by
              configuration). Anyone who knows the unguessable file link could download the file until
              it expires; do not share download links if the content is sensitive.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Short-term caption cache
            </h2>
            <p className="mt-3">
              To improve reliability and reduce load on third-party caption sources, we may cache
              caption/transcript data for a video for a limited period (on the order of hours, not
              permanent archives). This cache is operational, not a personal library or account
              history. It is separate from the short-lived download files described above.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Logs and operations
            </h2>
            <p className="mt-3">
              Like most hosted services, we may keep server logs for security, reliability, and abuse
              prevention (for example approximate timing, error codes, and rate-limit signals). We aim
              to avoid storing unnecessary detail. Internal dashboards may show aggregated usage
              metrics, not a permanent copy of your full transcript text, for operations.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Analytics
            </h2>
            <p className="mt-3">
              We may record anonymous product events (for example that an extraction succeeded or
              failed) and may use privacy-oriented web analytics (such as Vercel Analytics) to
              understand traffic and performance. Product events are designed not to include raw video
              URLs. Session identifiers used for analytics are not tied to a Transcript Flow account
              because basic use requires none.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Third-party services
            </h2>
            <p className="mt-3">
              YouTube and Vimeo are operated by third parties. Their handling of data is governed by
              their own terms and policies. Transcript Flow is not affiliated with Google or Vimeo.
              If we use error monitoring (for example Sentry), we configure it to reduce capture of
              request bodies and raw links where possible.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Contact
            </h2>
            <p className="mt-3">
              Questions about this policy:{" "}
              <a href={`mailto:${CONTACT_EMAIL}`} className="underline underline-offset-2" style={{ color: "var(--link)" }}>
                {CONTACT_EMAIL}
              </a>
              .
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
