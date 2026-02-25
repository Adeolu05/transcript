'use client';

import React, { useEffect, useRef } from 'react';
import Link from 'next/link';
import { Github, LayoutGrid } from 'lucide-react';
import { BotDemo } from './components/home/BotDemo';
import { HowItFlows } from './components/home/HowItFlows';
import { Capabilities } from './components/home/Capabilities';
import { Navbar } from '../components/Navbar';
import { JsonLd } from '../components/JsonLd';

const TELEGRAM_BOT_URL = 'https://t.me/TranscriptFlowBot';

const WEBSITE_SCHEMA = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "Transcript Flow",
  url: "https://usetranscriptflow.com",
};

const APP_SCHEMA = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "Transcript Flow",
  url: "https://usetranscriptflow.com/app",
  operatingSystem: "Web",
  applicationCategory: "UtilitiesApplication",
  offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
};

export default function Home() {
  const scrollToRef = useRef<((id: string) => void) | null>(null);

  useEffect(() => {
    scrollToRef.current = (id: string) => {
      document.querySelector(id)?.scrollIntoView({ behavior: 'smooth' });
    };
  }, []);

  return (
    <div className="landing overflow-x-hidden" style={{ background: 'var(--bg)', color: 'var(--text)' }}>
      <JsonLd data={WEBSITE_SCHEMA} />
      <JsonLd data={APP_SCHEMA} />
      {/* Navigation */}
      <Navbar
        links={[
          { label: 'Home', onClick: () => scrollToRef.current?.('#hero') },
          { label: 'App', href: '/app' },
          { label: 'Telegram', href: 'https://t.me/TranscriptFlowBot' },
        ]}
      />

      {/* Hero Section */}
      <header className="flex flex-col md:px-12 w-full min-h-[70vh] md:min-h-screen px-6 relative pt-20 pb-6 justify-end" id="hero">

        <div className="flex flex-col md:flex-row md:pb-12 w-full pb-6 items-end justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="reveal-text md:mb-0 md:w-auto w-full mb-6">
            <p className="md:text-base leading-relaxed text-sm font-normal tracking-wide max-w-md mb-6" style={{ color: 'var(--muted)' }}>
              Fast transcript extraction for YouTube and Vimeo. Paste a link. Get a clean file in seconds.
            </p>
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center gap-6">
                <Link
                  href="/app"
                  className="group inline-flex text-xs uppercase transition-all cursor-pointer font-bold tracking-[0.2em] px-6 py-3 rounded-full items-center gap-2"
                  style={{
                    color: 'var(--text)',
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid var(--border)',
                  }}
                >
                  Open App
                </Link>
                <a
                  href={TELEGRAM_BOT_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs uppercase transition-opacity hover:opacity-70 font-bold tracking-[0.2em] pb-1"
                  style={{ color: 'var(--muted)', borderBottom: '1px solid var(--border)' }}
                >
                  Open Telegram Bot
                </a>
              </div>
              <p className="text-sm font-medium" style={{ color: 'var(--muted)' }}>No account required.</p>
            </div>
          </div>

          <div className="text-left md:text-right reveal-text delay-100">
            <h1 className="md:text-[9vw] lg:text-[10vw] leading-[0.9] text-4xl sm:text-5xl font-semibold tracking-tighter pb-2"
              style={{ color: 'var(--link)' }}>
              Transcripts<br />from links.<br />Ready to<br />download.
            </h1>
          </div>
        </div>

        <div className="flex reveal-text delay-200 w-full pt-4 pb-4 items-center justify-between">
          <div className="flex gap-16">
            <div className="hidden md:block">
              <span className="text-xs font-medium tracking-widest lowercase flex items-center gap-3" style={{ color: 'var(--muted)' }}>
                <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--link)' }}></span>
                Status: Online
              </span>
            </div>
          </div>
          <div className="text-xs uppercase tracking-[0.3em] font-medium" style={{ color: 'rgba(255,255,255,0.2)' }}>
            scroll to process
          </div>
        </div>
      </header>

      {/* Manifesto */}
      <section className="px-6 md:px-12 py-16 md:py-24 flex justify-center items-center relative z-10" style={{ background: 'var(--bg)' }}>
        <h2 className="text-3xl md:text-5xl lg:text-6xl font-semibold leading-[1.15] tracking-tighter text-center max-w-5xl pb-2" style={{ color: 'var(--text)' }}>
          Stop rewinding videos for quotes. <span style={{ color: 'var(--link)' }}>Extract the transcript</span> and move on.
        </h2>
      </section>

      {/* How it flows */}
      <HowItFlows />

      {/* Capabilities */}
      <Capabilities />

      {/* Bot Demo Section */}
      <section id="demo" className="relative z-10 py-20" style={{ background: 'var(--bg)', borderTop: '1px solid var(--border)' }}>
        <div className="w-full max-w-6xl mx-auto px-6">
          <div className="text-center mb-10">
            <h2 className="text-4xl md:text-6xl font-bold tracking-tighter mb-4 pb-1" style={{ color: 'var(--link)' }}>
              Telegram delivery
            </h2>
            <p className="text-sm uppercase tracking-widest font-medium" style={{ color: 'var(--muted)' }}>Send a link. Get a file.</p>
          </div>
          <BotDemo />
        </div>
      </section>


      {/* Architecture Section */}
      <section id="studio" className="relative z-20" style={{ background: 'var(--bg)' }}>
        <div className="md:py-24 md:px-12 pt-16 pr-6 pb-16 pl-6" style={{ borderTop: '1px solid var(--border)' }}>
          <div className="max-w-7xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 lg:gap-24">
              <div>
                <h3 className="md:text-5xl lg:text-6xl leading-tight text-4xl font-semibold tracking-tighter mb-6" style={{ color: 'var(--link)' }}>Architecture</h3>
                <div className="w-20 h-[2px] mb-8" style={{ background: 'var(--primary)' }}></div>
              </div>
              <div className="flex flex-col justify-between h-full">
                <p className="md:text-xl leading-relaxed text-lg font-light tracking-tight max-w-xl mb-4" style={{ color: 'var(--muted)' }}>
                  A stateless extraction pipeline. Processing occurs in-memory.
                </p>

                <div className="grid grid-cols-3 gap-12 mt-12 pt-10" style={{ borderTop: '1px solid var(--border)' }}>
                  <div>
                    <span className="block text-sm uppercase font-bold tracking-[0.2em] mb-8" style={{ color: 'var(--text)' }}>Process</span>
                    <div className="flex flex-col gap-2 text-sm font-medium lowercase tracking-wider" style={{ color: 'var(--muted)' }}>
                      <span>extract stream</span>
                      <span className="opacity-50">↓</span>
                      <span>format output</span>
                      <span className="opacity-50">↓</span>
                      <span>serve file</span>
                    </div>
                  </div>
                  <div>
                    <span className="block text-sm uppercase font-bold tracking-[0.2em] mb-8" style={{ color: 'var(--text)' }}>Operations</span>
                    <ul className="space-y-4 text-sm font-medium lowercase tracking-wider" style={{ color: 'var(--muted)' }}>
                      <li>Extract stream</li>
                      <li>Format output text</li>
                      <li>Serve buffer</li>
                    </ul>
                  </div>
                  <div>
                    <span className="block text-sm uppercase font-bold tracking-[0.2em] mb-8" style={{ color: 'var(--text)' }}>Integration</span>
                    <ul className="text-sm font-medium space-y-4 tracking-wider" style={{ color: 'var(--muted)' }}>
                      <li>Web app</li>
                      <li>Telegram bot</li>
                      <li>API-ready architecture</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <footer id="contact" className="mt-20 pt-16" style={{ borderTop: '1px solid var(--border)' }}>
            <div className="max-w-7xl mx-auto">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-12">
                <div className="max-w-3xl">
                  <h4 className="text-5xl md:text-6xl lg:text-7xl font-semibold tracking-tighter leading-[1.15] mb-16 pb-2" style={{ color: 'var(--link)' }}>
                    Extract.<br />Download.<br />Done.
                  </h4>
                  <div className="flex flex-wrap items-center gap-6">
                    <a href="/app" className="inline-flex items-center gap-4 px-10 py-5 text-white font-bold text-[10px] uppercase tracking-widest transition-all rounded-full active:scale-[0.97]" style={{ background: 'var(--primary)' }}>
                      Open App
                    </a>
                    <a href="https://t.me/TranscriptFlowBot" target="_blank" className="inline-flex items-center gap-4 md:text-lg transition-opacity hover:opacity-70 group text-base font-semibold pb-2"
                      style={{ color: 'var(--muted)', borderBottom: '2px solid var(--border)' }}>
                      Open Telegram Bot
                    </a>
                  </div>
                </div>

                <div className="flex flex-col items-start md:items-end gap-10 w-full md:w-auto">
                  <div className="flex gap-6">
                    <a href="https://github.com/dpeluola" target="_blank" className="transition-opacity hover:opacity-70" style={{ color: 'var(--muted)' }}>
                      <Github className="h-6 w-6" />
                    </a>
                    <a href="#" className="transition-opacity hover:opacity-70" style={{ color: 'var(--muted)' }}>
                      <LayoutGrid className="h-6 w-6" />
                    </a>
                  </div>
                  <span className="text-xs font-semibold uppercase tracking-[0.4em]" style={{ color: 'var(--muted)' }}>
                    © 2026 Transcript Flow
                  </span>
                </div>
              </div>
            </div>
          </footer>
        </div>
      </section>
    </div>
  );
}
