import React from 'react';

export function HowItFlows() {
    return (
        <section className="px-6 md:px-12 py-20 relative z-10 w-full" style={{ background: 'var(--bg)' }}>
            <div className="max-w-4xl mx-auto flex flex-col items-center text-center">
                <h2 className="text-3xl md:text-4xl font-semibold tracking-tighter mb-2" style={{ color: 'var(--text)' }}>
                    How it flows
                </h2>
                <p className="text-sm uppercase tracking-widest font-medium mb-16" style={{ color: 'var(--muted)' }}>
                    From link to structured file.
                </p>

                {/* Flow Diagram */}
                <div className="flex flex-col md:flex-row items-center justify-center gap-6 w-full">
                    <FlowStep text="YouTube / Vimeo" />
                    <FlowArrow />
                    <FlowStep text="Extract captions" />
                    <FlowArrow />
                    <FlowStep text="Format clean text" />
                    <FlowArrow />
                    <FlowStep text="Download file" />
                </div>
            </div>
        </section>
    );
}

function FlowStep({ text }: { text: string }) {
    return (
        <div
            className="flex items-center justify-center px-6 py-4 border-precision w-full max-w-[240px] md:w-auto"
            style={{
                background: 'transparent',
                borderRadius: 'var(--radius)',
            }}
        >
            <span className="font-mono text-sm tracking-tight" style={{ color: 'var(--text)' }}>
                {text}
            </span>
        </div>
    );
}

function FlowArrow() {
    return (
        <>
            {/* Desktop Arrow */}
            <div className="hidden md:flex items-center justify-center px-2 opacity-80" style={{ color: 'var(--text)' }}>
                <span className="text-lg leading-none">→</span>
            </div>
            {/* Mobile Arrow */}
            <div className="flex md:hidden items-center justify-center py-2 opacity-80" style={{ color: 'var(--text)' }}>
                <span className="text-lg leading-none">↓</span>
            </div>
        </>
    );
}
