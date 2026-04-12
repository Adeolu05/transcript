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
          Last updated: March 2026. This page describes how we handle information in connection with{" "}
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
              file (for example TXT, PDF, or DOCX). You do not need an account to use the web app.
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
              Logs and operations
            </h2>
            <p className="mt-3">
              Like most hosted services, we may keep server logs for security, reliability, and abuse
              prevention (for example approximate timing and error codes). We aim to avoid storing
              unnecessary detail. Internal dashboards may show aggregated usage, not your transcript
              text, for operations.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Analytics
            </h2>
            <p className="mt-3">
              We may use privacy-oriented analytics (such as Vercel Analytics) to understand traffic
              and performance. Those tools typically do not use cookies for basic web vitals; refer
              to your browser and the provider’s documentation for details.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Third-party services
            </h2>
            <p className="mt-3">
              YouTube and Vimeo are operated by third parties. Their handling of data is governed by
              their own terms and policies. Transcript Flow is not affiliated with Google or Vimeo.
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
              . Update the address in code if you use a different inbox.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
