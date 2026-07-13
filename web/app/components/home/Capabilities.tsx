import React from 'react';

const items = [
    { label: 'Sources', description: 'YouTube and Vimeo links' },
    { label: 'Output', description: 'TXT (default), PDF, DOCX' },
    { label: 'Formatting', description: 'Clean text or timestamps' },
    { label: 'Preview', description: 'Short preview before download' },
    { label: 'Privacy', description: 'No account required' },
    { label: 'Limits', description: 'Rate limits apply.' },
];

export function Capabilities() {
    return (
        <section
            className="px-6 md:px-12 py-20 relative z-10 w-full"
            style={{ background: 'var(--bg)', borderTop: '1px solid var(--border)' }}
        >
            <div className="max-w-6xl mx-auto">
                <p
                    className="text-xs uppercase tracking-[0.3em] font-bold mb-4"
                    style={{ color: 'var(--muted)' }}
                >
                    Capabilities
                </p>
                <h2
                    className="text-2xl md:text-3xl font-semibold tracking-tighter mb-2"
                    style={{ color: 'var(--text)' }}
                >
                    Built for fast extraction.
                </h2>
                <p
                    className="text-sm tracking-wide mb-14"
                    style={{ color: 'var(--muted)' }}
                >
                    Anonymous by default. Reliable output formats.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    {items.map((item) => (
                        <div
                            key={item.label}
                            className="flex items-baseline justify-between px-8 py-4 select-none"
                            style={{
                                background: 'var(--surface)',
                                borderRadius: '8px',
                                border: '1px solid var(--border)',
                            }}
                        >
                            <span
                                className="text-sm font-medium tracking-tight"
                                style={{ color: 'var(--text)' }}
                            >
                                {item.label}
                            </span>
                            <span
                                className="text-sm tracking-wide text-right opacity-70"
                                style={{ color: 'var(--muted)' }}
                            >
                                {item.description}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
