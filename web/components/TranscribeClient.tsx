'use client';

import { useState, useRef, useEffect } from 'react';
import { ChevronRight } from 'lucide-react';
import { trackEvent } from '../lib/analytics';
import { PUBLIC_API_BASE } from '../lib/publicApiBase';

type UIState = 'idle' | 'processing' | 'success' | 'error';

interface SuccessData {
    provider: string;
    video_id: string;
    title: string;
    language: string;
    language_name: string;
    requested_language: string;
    source_language_name: string;
    translated: boolean;
    language_fallback: boolean;
    pdf_supported: boolean;
    duration_seconds: number;
    word_count: number;
    reading_time_seconds: number;
    file_id: string;
    file_download_url: string;
    preview_text: string;
    expires_at: string;
}

interface Summary {
    tldr: string;
    key_points: string[];
    chapters: { start_seconds: number; title: string }[];
}

interface ErrorData {
    code: string;
    message: string;
}

type DownloadFormat = 'txt' | 'pdf' | 'docx' | 'srt' | 'vtt';

interface Language {
    code: string;
    name: string;
    english_name: string;
}

// Used until /config answers (or if it fails)
const FALLBACK_LANGUAGES: Language[] = [{ code: 'en', name: 'English', english_name: 'English' }];
const LANGUAGE_KEY = 'tf_language';

// Per-viewer convenience only; storage can be unavailable (private mode, blocked site data)
function readStoredLanguage(): string | null {
    try {
        return localStorage.getItem(LANGUAGE_KEY);
    } catch {
        return null;
    }
}

function storeLanguage(code: string) {
    try {
        localStorage.setItem(LANGUAGE_KEY, code);
    } catch {
        /* ignore */
    }
}

// TXT is the primary action; the rest go through /convert.
const SECONDARY_FORMATS: { format: DownloadFormat; label: string }[] = [
    { format: 'pdf', label: 'PDF' },
    { format: 'docx', label: 'DOCX' },
    { format: 'srt', label: 'SRT' },
    { format: 'vtt', label: 'VTT' },
];

const STEPS = [
    'Extracting captions',
    'Formatting transcript',
    'Preparing preview',
];

function fmtDuration(s: number) {
    const m = Math.floor(s / 60);
    return `${m}:${String(s % 60).padStart(2, '0')}`;
}

function fmtTimestamp(total: number) {
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = String(total % 60).padStart(2, '0');
    return h ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`;
}

function fmtReading(s: number) {
    const m = Math.round(s / 60);
    return m <= 1 ? '<1 min' : `${m} min`;
}

export function TranscribeClient() {
    const [url, setUrl] = useState('');
    const [timestamps, setTimestamps] = useState(false);
    const [state, setState] = useState<UIState>('idle');
    const [step, setStep] = useState(0);
    const [success, setSuccess] = useState<SuccessData | null>(null);
    const [error, setError] = useState<ErrorData | null>(null);
    const [downloading, setDownloading] = useState<string | null>(null);
    const [convertError, setConvertError] = useState<string | null>(null);
    const [fileTtlHours, setFileTtlHours] = useState<number>(1);
    const [languages, setLanguages] = useState<Language[]>(FALLBACK_LANGUAGES);
    const [language, setLanguage] = useState('en');
    const [summariesEnabled, setSummariesEnabled] = useState(false);
    const [summary, setSummary] = useState<Summary | null>(null);
    const [summaryLoading, setSummaryLoading] = useState(false);
    const [summaryError, setSummaryError] = useState<string | null>(null);
    const resultRef = useRef<HTMLDivElement>(null);

    const API_BASE = PUBLIC_API_BASE;

    useEffect(() => {
        if ((state === 'success' || state === 'error') && resultRef.current) {
            setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 120);
        }
    }, [state]);

    // Fetch public config (file TTL, languages) on mount
    useEffect(() => {
        trackEvent('app_opened');
        fetch(`${API_BASE}/api/v1/config`)
            .then(r => r.json())
            .then(d => {
                if (!d.success) return;
                if (d.file_ttl_hours) setFileTtlHours(d.file_ttl_hours);
                setSummariesEnabled(Boolean(d.summaries_enabled));
                if (Array.isArray(d.languages) && d.languages.length) {
                    const list = d.languages as Language[];
                    setLanguages(list);
                    const stored = readStoredLanguage();
                    if (stored && list.some(l => l.code === stored)) setLanguage(stored);
                }
            })
            .catch(() => { });
    }, [API_BASE]);

    const handleLanguageChange = (code: string) => {
        setLanguage(code);
        storeLanguage(code);
        trackEvent('language_changed', { language: code });
    };

    const handleGenerate = async () => {
        if (!url.trim()) return;
        setState('processing');
        setStep(0);
        setSuccess(null);
        setError(null);
        setSummary(null);
        setSummaryError(null);
        trackEvent('extract_clicked', { include_timestamps: timestamps, language });

        const stepTimer = setInterval(() => {
            setStep(prev => (prev < 2 ? prev + 1 : prev));
        }, 2500);

        try {
            const res = await fetch(`${API_BASE}/api/v1/extract`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url.trim(),
                    include_timestamps: timestamps,
                    language,
                }),
            });

            const data = await res.json();
            clearInterval(stepTimer);

            if (data.success) {
                setStep(2);
                trackEvent('extract_succeeded', {
                    provider: data.provider,
                    duration_seconds_bucket: data.duration_seconds <= 600 ? '0-600' : data.duration_seconds <= 1800 ? '600-1800' : data.duration_seconds <= 3600 ? '1800-3600' : '3600+',
                    include_timestamps: timestamps,
                    language: data.language,
                    translated: Boolean(data.translated),
                });
                setTimeout(() => {
                    setSuccess(data as SuccessData);
                    setState('success');
                    trackEvent('preview_shown');
                }, 400);
            } else {
                const errCode = data.error?.code ?? 'UNKNOWN_ERROR';
                trackEvent('extract_failed', { error_code: errCode });
                setError(data.error ?? { code: 'UNKNOWN_ERROR', message: 'An unexpected error occurred.' });
                setState('error');
            }
        } catch {
            clearInterval(stepTimer);
            trackEvent('extract_failed', { error_code: 'NETWORK_ERROR' });
            setError({ code: 'NETWORK_ERROR', message: 'Could not reach the server. Check your connection and try again.' });
            setState('error');
        }
    };

    const handleDownload = async (format: DownloadFormat) => {
        if (!success) return;
        setDownloading(format);
        setConvertError(null);
        trackEvent('download_clicked', { file_format: format });

        try {
            // For TXT, use the direct download URL
            if (format === 'txt') {
                window.location.href = `${API_BASE}${success.file_download_url}`;
                trackEvent('download_succeeded', { file_format: format });
                setDownloading(null);
                return;
            }

            // Every other format is generated by the convert endpoint
            const res = await fetch(`${API_BASE}/api/v1/convert`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: success.file_id,
                    format: format,
                }),
            });

            const data = await res.json();
            if (data.success) {
                window.location.href = `${API_BASE}${data.file_download_url}`;
                trackEvent('download_succeeded', { file_format: format });
            } else {
                const fmt = format.toUpperCase();
                setConvertError(data.error?.message ?? `Could not generate ${fmt}. Try TXT or retry.`);
                trackEvent('download_failed', { file_format: format, error_code: data.error?.code ?? 'CONVERT_FAILED' });
            }
        } catch {
            const fmt = format.toUpperCase();
            setConvertError(`Could not generate ${fmt}. Try TXT or retry.`);
            trackEvent('download_failed', { file_format: format, error_code: 'NETWORK_ERROR' });
        } finally {
            setDownloading(null);
        }
    };

    const handleSummarize = async () => {
        if (!success) return;
        setSummaryLoading(true);
        setSummaryError(null);
        trackEvent('summary_clicked', { language: success.language });
        try {
            const res = await fetch(`${API_BASE}/api/v1/summarize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_id: success.file_id }),
            });
            const data = await res.json();
            if (data.success) {
                setSummary({ tldr: data.tldr, key_points: data.key_points, chapters: data.chapters });
                trackEvent('summary_succeeded', { cached: Boolean(data.cached) });
            } else {
                setSummaryError(data.error?.message ?? 'Could not generate a summary. Try again later.');
                trackEvent('summary_failed', { error_code: data.error?.code ?? 'UNKNOWN_ERROR' });
            }
        } catch {
            setSummaryError('Could not reach the server. Check your connection and try again.');
            trackEvent('summary_failed', { error_code: 'NETWORK_ERROR' });
        } finally {
            setSummaryLoading(false);
        }
    };

    const handleReset = () => {
        setSummary(null);
        setSummaryError(null);
        setState('idle');
        setUrl('');
        setSuccess(null);
        setError(null);
        setConvertError(null);
        setStep(0);
        trackEvent('new_transcript_clicked');
    };

    /* ─── FORM (shared between idle & processing) ────────────────── */
    const renderForm = () => {
        const isProcessing = state === 'processing';
        return (
            <div className="rounded-xl p-8 md:p-14 relative overflow-hidden transition-all duration-300"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
                {/* Input row */}
                <div className="flex flex-col md:flex-row gap-10 mb-10">
                    {/* URL */}
                    <div className="flex-grow relative pb-2 group" style={{ borderBottom: '1px solid var(--border)' }}>
                        <input
                            type="url"
                            value={url}
                            onChange={e => setUrl(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && !isProcessing && handleGenerate()}
                            placeholder="Paste a YouTube or Vimeo link"
                            disabled={isProcessing}
                            className="w-full bg-transparent px-0 py-4 focus:outline-none transition-all font-normal text-lg tracking-tight disabled:opacity-50"
                            style={{ color: 'var(--text)', caretColor: 'var(--primary)' }}
                        />
                        <div className="absolute bottom-0 left-0 h-[2px] w-0 group-focus-within:w-full transition-all duration-500"
                            style={{ background: 'var(--primary)' }} />
                    </div>

                    {/* Timestamps */}
                    <div className="flex-shrink-0 flex items-center gap-4 py-3 pb-2" style={{ borderBottom: '1px solid var(--border)' }}>
                        <span className="text-[10px] font-bold tracking-[0.3em] uppercase" style={{ color: 'var(--muted)' }}>Include timestamps</span>
                        <div className="flex">
                            <button
                                onClick={() => !isProcessing && setTimestamps(true)}
                                disabled={isProcessing}
                                className="px-3 py-1 text-[10px] font-bold uppercase tracking-widest transition-all cursor-pointer disabled:opacity-50"
                                style={{
                                    color: timestamps ? 'var(--primary)' : 'var(--muted)',
                                    borderBottom: timestamps ? '2px solid var(--primary)' : '2px solid transparent',
                                }}
                            >
                                On
                            </button>
                            <button
                                onClick={() => !isProcessing && setTimestamps(false)}
                                disabled={isProcessing}
                                className="px-3 py-1 text-[10px] font-bold uppercase tracking-widest transition-all cursor-pointer disabled:opacity-50"
                                style={{
                                    color: !timestamps ? 'var(--primary)' : 'var(--muted)',
                                    borderBottom: !timestamps ? '2px solid var(--primary)' : '2px solid transparent',
                                }}
                            >
                                Off
                            </button>
                        </div>
                    </div>
                </div>

                {/* Language */}
                <div className="-mt-4 mb-8 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
                    <label htmlFor="transcript-language" className="text-[10px] font-bold tracking-[0.3em] uppercase" style={{ color: 'var(--muted)' }}>
                        Transcript language
                    </label>
                    <select
                        id="transcript-language"
                        value={language}
                        onChange={e => handleLanguageChange(e.target.value)}
                        disabled={isProcessing}
                        className="bg-transparent py-1 pr-2 text-sm font-medium focus:outline-none cursor-pointer disabled:opacity-50"
                        style={{ color: 'var(--text)', borderBottom: '1px solid var(--border)' }}
                    >
                        {languages.map(l => (
                            <option key={l.code} value={l.code} style={{ background: 'var(--surface)', color: 'var(--text)' }}>
                                {l.name === l.english_name ? l.name : `${l.name} · ${l.english_name}`}
                            </option>
                        ))}
                    </select>
                    <p className="text-xs font-medium" style={{ color: 'var(--muted)' }}>
                        YouTube auto-translates when a video has no captions in this language.
                    </p>
                </div>

                {/* Generate / Extracting button */}
                <button
                    onClick={handleGenerate}
                    disabled={!url.trim() || isProcessing}
                    className="group relative inline-flex items-center gap-4 px-10 py-5 text-white font-bold text-[10px] uppercase tracking-[0.3em] rounded-full transition-all disabled:opacity-40 active:scale-[0.97] cursor-pointer"
                    style={{ background: 'var(--primary)' }}
                >
                    {isProcessing ? 'Extracting...' : 'Extract Transcript'}
                    {!isProcessing && <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />}
                </button>

                {/* Processing status list */}
                {isProcessing && (
                    <div className="mt-8 space-y-3">
                        {STEPS.map((label, i) => (
                            <div key={label} className="flex items-center gap-3">
                                <span
                                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                                    style={{ background: i <= step ? 'var(--primary)' : 'var(--border)' }}
                                />
                                <span
                                    className="text-sm font-medium tracking-tight"
                                    style={{ color: i <= step ? 'var(--text)' : 'var(--muted)', opacity: i <= step ? 1 : 0.5 }}
                                >
                                    {label}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    };

    /* ─── IDLE / PROCESSING ─────────────────────────────────────── */
    if (state === 'idle' || state === 'processing') {
        return renderForm();
    }

    /* ─── ERROR ─────────────────────────────────────────────────── */
    if (state === 'error' && error) {
        return (
            <div ref={resultRef} className="space-y-5">
                {renderForm()}
                <div className="rounded-xl p-8 md:p-12"
                    style={{ background: 'var(--surface)', border: '1px solid var(--danger)', boxShadow: 'var(--shadow)' }}>
                    <p className="text-[10px] font-bold tracking-[0.4em] uppercase mb-4" style={{ color: 'var(--danger)' }}>Error</p>
                    <h3 className="text-xl font-semibold tracking-tighter mb-4" style={{ color: 'var(--text)' }}>Transcript extraction failed.</h3>
                    <p className="text-sm font-medium mb-6" style={{ color: 'var(--muted)' }}>{error.message}</p>
                    <button
                        onClick={handleReset}
                        className="group inline-flex items-center gap-3 text-[10px] font-bold uppercase tracking-[0.3em] transition-opacity hover:opacity-70 pb-2 cursor-pointer"
                        style={{ color: 'var(--muted)', borderBottom: '1px solid var(--border)' }}
                    >
                        Try Again
                        <ChevronRight className="w-3 h-3 transition-transform group-hover:translate-x-1" />
                    </button>
                </div>
            </div>
        );
    }

    /* ─── SUCCESS ───────────────────────────────────────────────── */
    if (state === 'success' && success) {
        const chips = [
            { label: 'Title', value: success.title },
            { label: 'Language', value: success.language_name },
            { label: 'Duration', value: fmtDuration(success.duration_seconds) },
            { label: 'Words', value: success.word_count.toLocaleString() },
            { label: 'Read time', value: fmtReading(success.reading_time_seconds) },
        ];

        return (
            <div ref={resultRef} className="space-y-5 reveal-text">
                {/* Summary block */}
                <div className="rounded-xl overflow-hidden"
                    style={{ background: 'var(--surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
                    {/* Header */}
                    <div className="px-8 md:px-12 py-8" style={{ borderBottom: '1px solid var(--border)' }}>
                        <p className="text-[9px] font-bold tracking-[0.5em] uppercase mb-3" style={{ color: 'var(--success)' }}>Transcript ready</p>
                        <h3 className="text-xl md:text-2xl font-semibold tracking-tighter leading-snug" style={{ color: 'var(--text)' }}>
                            {success.title}
                        </h3>
                    </div>

                    {/* Metadata chips */}
                    <div className="px-8 md:px-12 py-6 flex flex-wrap gap-8">
                        {chips.map(c => (
                            <div key={c.label} className="flex flex-col gap-1">
                                <span className="text-[9px] font-bold uppercase tracking-[0.4em]" style={{ color: 'var(--muted)' }}>{c.label}</span>
                                <span className="text-sm font-medium lowercase" style={{ color: 'var(--text)' }}>{c.value}</span>
                            </div>
                        ))}
                    </div>

                    {/* What language actually came back */}
                    {(success.translated || success.language_fallback) && (
                        <p className="px-8 md:px-12 pb-6 -mt-2 text-xs font-medium" style={{ color: 'var(--muted)' }}>
                            {success.translated
                                ? `Auto-translated by YouTube from ${success.source_language_name}. Machine translation can contain mistakes.`
                                : `${languages.find(l => l.code === success.requested_language)?.name ?? success.requested_language} captions weren't available for this video, so this transcript is in ${success.language_name}.`}
                        </p>
                    )}
                </div>

                {/* Preview block */}
                <div className="rounded-xl overflow-hidden"
                    style={{ background: 'var(--surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
                    <div className="px-8 md:px-12 py-5" style={{ borderBottom: '1px solid var(--border)' }}>
                        <p className="text-[10px] font-bold tracking-[0.4em] uppercase" style={{ color: 'var(--muted)' }}>Preview (truncated)</p>
                    </div>
                    <div
                        dir="auto"
                        className="px-6 py-6 overflow-y-auto text-sm leading-relaxed whitespace-pre-wrap"
                        style={{
                            maxHeight: '360px',
                            color: 'var(--text)',
                            background: 'var(--bg)',
                            borderBottom: '1px solid var(--border)',
                        }}
                    >
                        {success.preview_text}
                    </div>
                    <div className="px-8 md:px-12 py-4">
                        <p className="text-xs font-medium" style={{ color: 'var(--muted)' }}>
                            Showing shortened preview. Download for the full transcript.
                        </p>
                    </div>
                </div>

                {/* AI summary */}
                {summariesEnabled && (
                    <div className="rounded-xl px-8 md:px-12 py-8"
                        style={{ background: 'var(--surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
                        <p className="text-[10px] font-bold tracking-[0.4em] uppercase mb-4" style={{ color: 'var(--muted)' }}>AI summary</p>
                        {summary ? (
                            <div dir="auto" className="space-y-6 text-sm leading-relaxed" style={{ color: 'var(--text)' }}>
                                <p>{summary.tldr}</p>
                                {summary.key_points.length > 0 && (
                                    <ul className="list-disc pl-5 space-y-1.5">
                                        {summary.key_points.map((point, i) => <li key={i}>{point}</li>)}
                                    </ul>
                                )}
                                {summary.chapters.length > 0 && (
                                    <div>
                                        <p className="text-[10px] font-bold tracking-[0.3em] uppercase mb-2" style={{ color: 'var(--muted)' }}>Chapters</p>
                                        <ol className="space-y-1">
                                            {summary.chapters.map(c => (
                                                <li key={`${c.start_seconds}-${c.title}`} className="flex gap-3">
                                                    {success.provider === 'youtube' ? (
                                                        <a
                                                            href={`https://www.youtube.com/watch?v=${encodeURIComponent(success.video_id)}&t=${c.start_seconds}s`}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="tabular-nums font-medium underline-offset-2 hover:underline"
                                                            style={{ color: 'var(--primary)' }}
                                                        >
                                                            {fmtTimestamp(c.start_seconds)}
                                                        </a>
                                                    ) : (
                                                        <span className="tabular-nums font-medium" style={{ color: 'var(--muted)' }}>{fmtTimestamp(c.start_seconds)}</span>
                                                    )}
                                                    <span>{c.title}</span>
                                                </li>
                                            ))}
                                        </ol>
                                    </div>
                                )}
                                <p className="text-xs" style={{ color: 'var(--muted)' }}>Generated by AI from the captions and may contain mistakes.</p>
                            </div>
                        ) : (
                            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                                <button
                                    onClick={handleSummarize}
                                    disabled={summaryLoading}
                                    className="inline-flex items-center gap-3 px-8 py-4 font-bold text-[10px] uppercase tracking-widest transition-all rounded-full active:scale-[0.97] cursor-pointer disabled:opacity-40"
                                    style={{ color: 'var(--text)', border: '1px solid var(--border)', background: 'transparent' }}
                                >
                                    {summaryLoading ? 'Summarizing...' : 'Summarize with AI'}
                                </button>
                                <p className="text-xs font-medium" style={{ color: summaryError ? 'var(--danger)' : 'var(--muted)' }}>
                                    {summaryError ?? 'TL;DR, key points and chapters. Sends the transcript to Anthropic (Claude) to generate it.'}
                                </p>
                            </div>
                        )}
                    </div>
                )}

                {/* Download controls */}
                <div className="rounded-xl px-8 md:px-12 py-8 flex flex-col sm:flex-row sm:flex-wrap items-start sm:items-center gap-4"
                    style={{ background: 'var(--surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
                    {/* TXT — primary */}
                    <button
                        onClick={() => handleDownload('txt')}
                        disabled={downloading !== null}
                        className="inline-flex items-center gap-3 px-8 py-4 text-white font-bold text-[10px] uppercase tracking-widest transition-all rounded-full active:scale-[0.97] cursor-pointer disabled:opacity-40"
                        style={{ background: 'var(--primary)' }}
                    >
                        {downloading === 'txt' ? 'Preparing...' : 'Download TXT'}
                    </button>
                    {SECONDARY_FORMATS.map(({ format, label }) => (
                        <button
                            key={format}
                            onClick={() => handleDownload(format)}
                            disabled={downloading !== null || (format === 'pdf' && !success.pdf_supported)}
                            title={format === 'pdf' && !success.pdf_supported ? "PDF isn't available for this language yet. Use DOCX or TXT." : undefined}
                            className="inline-flex items-center gap-3 px-8 py-4 font-bold text-[10px] uppercase tracking-widest transition-all rounded-full active:scale-[0.97] cursor-pointer disabled:opacity-40"
                            style={{ color: 'var(--text)', border: '1px solid var(--border)', background: 'transparent' }}
                        >
                            {downloading === format ? 'Preparing...' : `Download ${label}`}
                        </button>
                    ))}

                    {/* New Transcript link */}
                    <button
                        onClick={handleReset}
                        className="group inline-flex items-center gap-3 text-[10px] font-bold uppercase tracking-[0.3em] transition-opacity hover:opacity-70 pb-2 cursor-pointer sm:ml-auto"
                        style={{ color: 'var(--muted)', borderBottom: '1px solid var(--border)' }}
                    >
                        New Transcript
                        <ChevronRight className="w-3 h-3 transition-transform group-hover:translate-x-1" />
                    </button>
                </div>

                {!success.pdf_supported && (
                    <p className="text-xs font-medium" style={{ color: 'var(--muted)' }}>
                        PDF isn&apos;t available for this language yet. DOCX, TXT, SRT and VTT work normally.
                    </p>
                )}

                {/* Convert error message */}
                {convertError && (
                    <div className="rounded-xl px-8 md:px-12 py-5"
                        style={{ background: 'var(--surface)', border: '1px solid var(--danger)', boxShadow: 'var(--shadow)' }}>
                        <p className="text-sm font-medium" style={{ color: 'var(--danger)' }}>
                            {convertError}
                        </p>
                    </div>
                )}

                <p className="text-[10px] font-bold tracking-[0.3em] uppercase" style={{ color: 'var(--muted)' }}>
                    Files expire after {fileTtlHours === 1 ? '1 hour' : `${fileTtlHours} hours`}.
                    {success.expires_at && (
                        <> Expires at {new Date(success.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.</>)}
                </p>
            </div>
        );
    }

    return null;
}
