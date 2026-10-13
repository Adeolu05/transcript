import React from 'react';
import Link from 'next/link';
import { CONTACT_EMAIL } from '../../../lib/site';

const plans = [
    {
        name: 'Free',
        status: 'Available now',
        blurb: 'No account. Open the app and go.',
        features: [
            'YouTube and Vimeo transcripts',
            'TXT, PDF, DOCX, SRT and VTT downloads',
            '23 languages',
            'Daily allowance of AI summaries, cleanup and notes',
            'Telegram bot included',
        ],
        cta: { label: 'Open App', href: '/app' },
    },
    {
        name: 'Pro',
        status: 'Coming soon',
        blurb: 'For creators, students and teams who use it every day.',
        features: [
            'Much higher daily limits',
            'Ask questions across a video or a whole playlist, with timestamped answers',
            'Saved history and bulk export',
            'Priority processing for long videos',
            'API access',
        ],
        cta: {
            label: 'Join the early-access list',
            href: `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent('Transcript Flow Pro early access')}`,
        },
    },
];

export function Pricing() {
    return (
        <section
            id="pricing"
            className="px-6 md:px-12 py-20 relative z-10 w-full"
            style={{ background: 'var(--bg)', borderTop: '1px solid var(--border)' }}
        >
            <div className="max-w-6xl mx-auto">
                <p className="text-xs uppercase tracking-[0.3em] font-bold mb-4" style={{ color: 'var(--muted)' }}>
                    Plans
                </p>
                <h2 className="text-2xl md:text-3xl font-semibold tracking-tighter mb-2" style={{ color: 'var(--text)' }}>
                    Free to start. Pro when you need more.
                </h2>
                <p className="text-sm tracking-wide mb-14" style={{ color: 'var(--muted)' }}>
                    The free plan stays free. Pro is in development; tell us what you need.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {plans.map((plan) => (
                        <div
                            key={plan.name}
                            className="px-8 py-8 flex flex-col"
                            style={{ background: 'var(--surface)', borderRadius: '8px', border: '1px solid var(--border)' }}
                        >
                            <div className="flex items-baseline justify-between mb-2">
                                <span className="text-xl font-semibold tracking-tight" style={{ color: 'var(--text)' }}>
                                    {plan.name}
                                </span>
                                <span className="text-[10px] font-bold uppercase tracking-[0.3em]" style={{ color: 'var(--muted)' }}>
                                    {plan.status}
                                </span>
                            </div>
                            <p className="text-sm mb-6" style={{ color: 'var(--muted)' }}>{plan.blurb}</p>
                            <ul className="space-y-2 text-sm mb-8 flex-grow" style={{ color: 'var(--text)' }}>
                                {plan.features.map((f) => (
                                    <li key={f} className="flex gap-3">
                                        <span style={{ color: 'var(--primary)' }}>&bull;</span>
                                        <span>{f}</span>
                                    </li>
                                ))}
                            </ul>
                            {plan.cta.href.startsWith('/') ? (
                                <Link
                                    href={plan.cta.href}
                                    className="inline-flex self-start items-center px-8 py-4 text-white font-bold text-[10px] uppercase tracking-widest rounded-full transition-all active:scale-[0.97]"
                                    style={{ background: 'var(--primary)' }}
                                >
                                    {plan.cta.label}
                                </Link>
                            ) : (
                                <a
                                    href={plan.cta.href}
                                    className="inline-flex self-start items-center px-8 py-4 font-bold text-[10px] uppercase tracking-widest rounded-full transition-all active:scale-[0.97]"
                                    style={{ color: 'var(--text)', border: '1px solid var(--border)' }}
                                >
                                    {plan.cta.label}
                                </a>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
