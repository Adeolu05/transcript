'use client';

import React, { useState, useRef } from 'react';
import { CheckCircle2, AlertCircle, Copy, Download, Youtube, Video, ChevronRight } from 'lucide-react';
import { ProcessingStatus, TranscriptResult, FileFormat } from '../../types';

export const Generator: React.FC = () => {
    const [url, setUrl] = useState('');
    const [status, setStatus] = useState<ProcessingStatus>(ProcessingStatus.IDLE);
    const [result, setResult] = useState<TranscriptResult | null>(null);
    const [format, setFormat] = useState<FileFormat>('txt');
    const [error, setError] = useState<string | null>(null);
    const [downloadUrl, setDownloadUrl] = useState<string>('');

    const resultRef = useRef<HTMLDivElement>(null);

    const handleGenerate = async () => {
        if (!url) return;
        setError(null);
        setResult(null);
        setDownloadUrl('');
        setStatus(ProcessingStatus.ANALYZING);

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            setStatus(ProcessingStatus.EXTRACTING);

            const response = await fetch(`${apiUrl}/api/v1/extract`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url,
                    format: format,
                    include_timestamps: false,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'extraction failed');
            }

            setStatus(ProcessingStatus.FORMATTING);

            const data = await response.json();

            setDownloadUrl(`${apiUrl}${data.file_download_url}`);

            setResult({
                videoId: extractVideoId(url),
                title: data.video_title || 'video transcript',
                segments: [], // Raw text isn't returned in the JSON for V1 anymore
                summary: `processed ${data.word_count} words. archival artifact generated.`,
            });

            setStatus(ProcessingStatus.COMPLETE);
            setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
        } catch (err: any) {
            setError(err.message || "unexpected engine error.");
            setStatus(ProcessingStatus.ERROR);
        }
    };

    const extractVideoId = (url: string): string => {
        const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|vimeo\.com\/)([^&\s]+)/);
        return match ? match[1] : 'unknown';
    };

    const handleCopy = async () => {
        if (result) {
            const text = result.segments.map(s => s.text).join('\n');
            await navigator.clipboard.writeText(text);
        }
    };

    const handleDownload = () => {
        if (downloadUrl) {
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `transcript.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    };

    const isProcessing = [ProcessingStatus.ANALYZING, ProcessingStatus.EXTRACTING, ProcessingStatus.FORMATTING].includes(status);

    return (
        <div className="py-20 md:py-28 px-6 md:px-12 max-w-7xl mx-auto bg-[#000000] relative">
            {/* Colorful Background Glow */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[60vw] h-[60vw] bg-gradient-to-br from-purple-500/10 via-pink-500/10 to-cyan-500/10 rounded-full blur-[150px] -z-10" />

            <div className="mb-16 flex flex-col md:flex-row justify-between items-start md:items-end gap-10">
                <div className="max-w-xl">
                    <h2 className="md:text-6xl lowercase text-5xl font-semibold bg-gradient-to-r from-purple-400 via-pink-400 to-cyan-400 bg-clip-text text-transparent tracking-tighter mb-4 font-geist">
                        extraction engine
                    </h2>
                    <p className="text-neutral-500 lowercase text-sm tracking-widest font-medium uppercase">
                        v2.8.1 / stable / zero-latency
                    </p>
                </div>
                <div className="flex items-center gap-6">
                    <span className="text-[10px] font-bold tracking-[0.5em] text-neutral-800 uppercase font-geist">processing.online</span>
                </div>
            </div>

            <div className="bg-gradient-to-br from-purple-950/20 via-pink-950/10 to-cyan-950/20 border-2 border-purple-500/20 rounded-lg p-8 md:p-16 relative overflow-hidden transition-all duration-700 hover:border-purple-400/40 hover:shadow-[0_0_40px_rgba(168,85,247,0.2)]">
                <div className="flex flex-col md:flex-row gap-10 mb-12">
                    <div className="flex-grow relative border-b border-neutral-800 pb-2 group">
                        <input
                            type="text"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="https://content-url.com"
                            className="w-full bg-transparent text-white px-0 py-4 focus:outline-none transition-all font-normal placeholder-neutral-800 text-lg tracking-tight"
                            disabled={isProcessing}
                        />
                        <div className="absolute bottom-0 left-0 h-[2px] w-0 bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 group-focus-within:w-full transition-all duration-500"></div>
                        <div className="absolute right-0 top-1/2 -translate-y-1/2 opacity-20">
                            <Youtube className="w-6 h-6 text-white" />
                        </div>
                    </div>

                    <div className="flex-shrink-0 min-w-[200px] border-b border-neutral-800 pb-2">
                        <select
                            value={format}
                            onChange={(e) => setFormat(e.target.value as FileFormat)}
                            className="w-full bg-transparent text-neutral-400 px-0 py-4 focus:outline-none cursor-pointer hover:text-white transition-colors text-sm appearance-none lowercase tracking-wide font-medium"
                            disabled={isProcessing}
                        >
                            <option value="txt" className="bg-black">format: txt</option>
                            <option value="docx" className="bg-black">format: docx</option>
                            <option value="pdf" className="bg-black">format: pdf</option>
                        </select>
                    </div>
                </div>

                <button
                    onClick={handleGenerate}
                    disabled={!url || isProcessing}
                    className="group relative inline-flex items-center gap-4 px-12 py-6 bg-gradient-to-r from-purple-500 via-pink-500 to-cyan-500 hover:from-purple-600 hover:via-pink-600 hover:to-cyan-600 text-white font-bold text-[10px] uppercase tracking-[0.3em] rounded-full transition-all disabled:opacity-20 active:scale-95 shadow-[0_0_30px_rgba(168,85,247,0.3)]"
                >
                    {isProcessing ? (
                        <span className="flex items-center gap-3">
                            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                            processing...
                        </span>
                    ) : (
                        <>
                            initialize engine
                            <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                        </>
                    )}
                </button>

                {error && (
                    <div className="mt-12 p-5 border border-red-500/40 rounded-lg flex items-center gap-4 text-red-400 bg-red-950/20">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        <span className="text-[10px] uppercase tracking-widest font-bold">{error}</span>
                    </div>
                )}
            </div>

            {/* Results View */}
            {result && downloadUrl && (
                <div ref={resultRef} className="mt-20 reveal-text">
                    <div className="bg-gradient-to-br from-cyan-950/20 via-purple-950/20 to-pink-950/20 border-2 border-cyan-500/20 rounded-lg overflow-hidden hover:border-cyan-400/40 transition-all duration-500">
                        <div className="px-10 py-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-10">
                            <div>
                                <h3 className="text-white font-semibold text-2xl lowercase font-geist tracking-tighter">{result.title}</h3>
                                <div className="flex items-center gap-4 mt-2">
                                    <span className="text-[9px] uppercase font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent tracking-[0.4em]">
                                        id: {result.videoId}
                                    </span>
                                </div>
                            </div>

                            <button
                                onClick={handleDownload}
                                className="flex-1 md:flex-none flex items-center justify-center gap-2 px-12 py-5 bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-600 hover:to-purple-600 text-white font-bold text-[10px] uppercase tracking-widest transition-all rounded-lg shadow-[0_0_20px_rgba(0,212,255,0.3)] w-full">
                                download archive
                            </button>
                        </div>

                        <div className="p-10 border-t border-neutral-800">
                            <p className="text-neutral-500 text-xs leading-loose lowercase font-medium tracking-wide italic">
                                {result.summary}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

