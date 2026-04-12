import type { Metadata } from "next";
import Link from "next/link";
import { CONTACT_EMAIL, SITE_URL } from "../../lib/site";

export const metadata: Metadata = {
  title: "Terms of use",
  description: "Terms of use for Transcript Flow — transcript extraction for YouTube and Vimeo links.",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
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
          Terms of use
        </h1>
        <p className="mt-4 text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
          Last updated: March 2026. These terms govern use of {SITE_URL}. They are a practical draft;
          have a lawyer adapt them for your jurisdiction and product.
        </p>

        <div className="mt-12 space-y-8 text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              The service
            </h2>
            <p className="mt-3">
              Transcript Flow provides tools to obtain text transcripts from supported public video
              links. Features, limits, and availability may change. The service is provided “as is”
              without warranties of any kind, to the extent permitted by law.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Acceptable use
            </h2>
            <p className="mt-3">
              You agree not to misuse the service: no unlawful activity, no attempts to overwhelm
              infrastructure, no scraping or automation that violates our rate limits or fair use,
              and no use to infringe others’ intellectual property or privacy. You are responsible
              for links you submit and for complying with YouTube, Vimeo, and applicable law.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Rate limits
            </h2>
            <p className="mt-3">
              We may apply technical limits (for example per day per connection) to keep the service
              reliable for everyone. Excessive or abusive use may be throttled or blocked.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Intellectual property
            </h2>
            <p className="mt-3">
              Transcript content originates from third-party platforms and creators. You are
              responsible for how you use downloaded text. The Transcript Flow name, site, and
              software are owned by their respective rights holders.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Limitation of liability
            </h2>
            <p className="mt-3">
              To the maximum extent permitted by law, Transcript Flow and its operators are not
              liable for indirect, incidental, or consequential damages, or for loss of data or
              profits, arising from your use of the service.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Contact
            </h2>
            <p className="mt-3">
              <a href={`mailto:${CONTACT_EMAIL}`} className="underline underline-offset-2" style={{ color: "var(--link)" }}>
                {CONTACT_EMAIL}
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
