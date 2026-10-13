import React from 'react';

const tools = [
    {
        label: 'AI cleanup',
        description: 'Turns raw auto-captions into readable text: punctuation, paragraphs and speaker labels, with nothing summarised away.',
    },
    {
        label: 'Summary & chapters',
        description: 'A TL;DR, key points and timestamped chapters you can jump to, in the language you pick.',
    },
    {
        label: 'Study notes',
        description: 'Sections, key ideas and review questions, ready to revise from.',
    },
    {
        label: 'Blog post & show notes',
        description: 'An original article, or episode notes with takeaways and timestamps, written from the video.',
    },
    {
        label: '23 languages',
        description: 'Get the transcript, and every AI output, in the language you read best.',
    },
    {
        label: 'Any format',
        description: 'Download everything as TXT, DOCX or PDF. Captions also export as SRT and VTT.',
    },
];

export function AiTools() {
    return (
        <section
            id="ai"
            className="px-6 md:px-12 py-20 relative z-10 w-full"
            style={{ background: 'var(--bg)', borderTop: '1px solid var(--border)' }}
        >
            <div className="max-w-6xl mx-auto">
                <p className="text-xs uppercase tracking-[0.3em] font-bold mb-4" style={{ color: 'var(--muted)' }}>
                    Powered by Claude
                </p>
                <h2 className="text-2xl md:text-3xl font-semibold tracking-tighter mb-2" style={{ color: 'var(--text)' }}>
                    From a link to something you can use.
                </h2>
                <p className="text-sm tracking-wide mb-14 max-w-2xl" style={{ color: 'var(--muted)' }}>
                    Extraction is the start. Transcript Flow uses Claude, built by Anthropic, to clean, summarise and
                    reshape what a video says. AI runs only when you ask, and files are short-lived.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    {tools.map((tool) => (
                        <div
                            key={tool.label}
                            className="px-8 py-6"
                            style={{ background: 'var(--surface)', borderRadius: '8px', border: '1px solid var(--border)' }}
                        >
                            <span className="block text-sm font-semibold tracking-tight mb-2" style={{ color: 'var(--text)' }}>
                                {tool.label}
                            </span>
                            <span className="block text-sm leading-relaxed" style={{ color: 'var(--muted)' }}>
                                {tool.description}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
