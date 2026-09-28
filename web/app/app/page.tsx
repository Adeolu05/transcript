'use client';

import React from 'react';
import { TranscribeClient } from '../../components/TranscribeClient';
import { Navbar } from '../../components/Navbar';
import { SiteFooter } from '../../components/SiteFooter';

export default function AppPage() {
    return (
        <div className="min-h-screen overflow-x-hidden" style={{ background: 'var(--bg)', color: 'var(--text)' }}>

            {/* Navigation */}
            <Navbar
                links={[
                    { label: 'Home', href: '/' },
                    { label: 'Telegram', href: 'https://t.me/TranscriptFlowBot' },
                ]}
                showThemeToggle
            />

            {/* Main Content */}
            <header className="flex flex-col md:px-12 w-full pr-6 pl-6 relative pt-24 pb-12">

                {/* Heading */}
                <div className="flex flex-col md:flex-row md:pb-10 w-full pb-8 items-end justify-between mb-10"
                    style={{ borderBottom: '1px solid var(--border)' }}>
                    <div className="reveal-text md:mb-0 md:w-auto w-full mb-8">
                        <p className="md:text-base leading-relaxed text-sm font-normal tracking-wide max-w-md mb-5"
                            style={{ color: 'var(--muted)' }}>
                            Paste a YouTube or Vimeo link to generate a transcript file.
                        </p>
                        <div className="flex items-center gap-3">
                            <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--success)' }} />
                            <span className="text-xs font-medium tracking-widest" style={{ color: 'var(--muted)' }}>Status: Online</span>
                        </div>
                    </div>
                    <div className="text-left md:text-right reveal-text delay-100">
                        <h1 className="md:text-[7vw] lg:text-[8vw] leading-[0.9] text-3xl sm:text-4xl font-semibold tracking-tighter pb-2"
                            style={{ color: 'var(--primary)' }}>
                            Transcript<br />generator
                        </h1>
                    </div>
                </div>

                {/* Tool section */}
                <div className="reveal-text delay-200 max-w-7xl w-full">
                    <div className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
                        <div className="max-w-xl">
                            <h2 className="md:text-5xl text-4xl font-semibold tracking-tighter mb-3"
                                style={{ color: 'var(--primary)' }}>
                                Transcript generator
                            </h2>
                            <p className="text-xs tracking-widest font-medium" style={{ color: 'var(--muted)' }}>
                                Fast. Reliable. Anonymous.
                            </p>
                        </div>
                    </div>

                    <TranscribeClient />
                </div>
            </header>

            {/* How It Works */}
            <section className="py-12 md:py-16 px-6 md:px-12 relative" style={{ borderTop: '1px solid var(--border)' }}>
                <div className="max-w-7xl mx-auto">
                    <div className="mb-8">
                        <span className="text-[10px] font-bold tracking-[0.5em] uppercase" style={{ color: 'var(--muted)' }}>how it works</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
                        {[
                            { num: '01', title: 'Paste link', desc: 'Add a YouTube or Vimeo URL.' },
                            { num: '02', title: 'Choose output', desc: 'TXT, PDF, DOCX, SRT, or VTT. Optional timestamps.' },
                            { num: '03', title: 'Download', desc: 'Preview in-page, then download the full file.' },
                        ].map(step => (
                            <div key={step.num} className="group">
                                <span className="text-3xl font-bold tracking-tighter" style={{ color: 'var(--primary)' }}>
                                    {step.num}
                                </span>
                                <div className="h-[1px] my-5 group-hover:w-16 w-8 transition-all duration-500" style={{ background: 'var(--border)' }} />
                                <h3 className="text-lg font-semibold tracking-tight mb-3" style={{ color: 'var(--text)' }}>
                                    {step.title}
                                </h3>
                                <p className="text-sm leading-relaxed" style={{ color: 'var(--muted)' }}>
                                    {step.desc}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            <SiteFooter />
        </div>
    );
}
