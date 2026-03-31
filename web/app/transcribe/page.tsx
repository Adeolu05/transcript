'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { TranscribeClient } from '../../components/TranscribeClient';

export default function TranscribePage() {
    return (
        <div className="min-h-screen overflow-x-hidden" style={{ background: 'var(--bg)', color: 'var(--text)' }}>
            <div className="container mx-auto px-6 py-12 max-w-5xl">
                <Link
                    href="/"
                    className="inline-flex items-center gap-2 mb-10 text-[10px] font-bold uppercase tracking-widest transition-opacity hover:opacity-70"
                    style={{ color: 'var(--muted)' }}
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Home
                </Link>
                <TranscribeClient />
            </div>
        </div>
    );
}
