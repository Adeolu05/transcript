import Link from "next/link";
import { Github } from "lucide-react";
import { GITHUB_PUBLIC_URL, TELEGRAM_BOT_URL } from "../lib/site";

const linkClass =
  "text-[10px] font-semibold uppercase tracking-[0.25em] transition-opacity hover:opacity-70";

const muted = "var(--muted)";

export function SiteFooter() {
  return (
    <footer
      className="w-full px-6 md:px-12 py-10 md:py-12"
      style={{
        borderTop: "1px solid var(--border)",
        background: "var(--bg)",
      }}
    >
      <div className="max-w-7xl mx-auto flex flex-col gap-10 md:flex-row md:items-start md:justify-between">
        <div className="flex flex-col gap-4">
          <span
            className="text-xs font-semibold uppercase tracking-[0.35em]"
            style={{ color: muted }}
          >
            Transcript Flow
          </span>
          <nav className="flex flex-wrap gap-x-8 gap-y-3" aria-label="Footer">
            <Link href="/app" className={linkClass} style={{ color: muted }}>
              App
            </Link>
            <a
              href={TELEGRAM_BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className={linkClass}
              style={{ color: muted }}
            >
              Telegram
            </a>
            <Link href="/privacy" className={linkClass} style={{ color: muted }}>
              Privacy
            </Link>
            <Link href="/terms" className={linkClass} style={{ color: muted }}>
              Terms
            </Link>
          </nav>
        </div>

        <div className="flex flex-col gap-6 md:items-end">
          <div className="flex items-center gap-5">
            <a
              href={GITHUB_PUBLIC_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="transition-opacity hover:opacity-70"
              style={{ color: muted }}
              aria-label="GitHub"
            >
              <Github className="h-5 w-5" />
            </a>
          </div>
          <p className="text-[10px] leading-relaxed max-w-sm md:text-right" style={{ color: muted }}>
            YouTube and Vimeo are trademarks of their respective owners. Transcript Flow is not
            affiliated with or endorsed by them.
          </p>
          <p className="text-[10px] uppercase tracking-[0.35em]" style={{ color: muted }}>
            © {new Date().getFullYear()} Transcript Flow
          </p>
        </div>
      </div>
    </footer>
  );
}
