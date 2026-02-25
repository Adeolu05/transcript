'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Loader2, Download, CheckCircle2 } from 'lucide-react';

export default function TranscribePage() {
    const [url, setUrl] = useState('');
    const [format, setFormat] = useState<'clean' | 'timestamp' | 'paragraph'>('clean');
    const [fileType, setFileType] = useState<'txt' | 'docx' | 'pdf'>('txt');
    const [loading, setLoading] = useState(false);
    const [downloadUrl, setDownloadUrl] = useState('');
    const [metadata, setMetadata] = useState<{ title: string, words: number, time: number } | null>(null);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setDownloadUrl('');
        setLoading(true);

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${apiUrl}/api/v1/extract`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url,
                    format: fileType,
                    include_timestamps: format === 'timestamp',
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to generate transcript');
            }

            // Consume JSON rather than blob
            const data = await response.json();

            setMetadata({
                title: data.video_title,
                words: data.word_count,
                time: data.reading_time,
            });

            setDownloadUrl(`${apiUrl}${data.file_download_url}`);

        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-violet-50 via-purple-50 to-blue-50">
            <div className="container mx-auto px-6 py-12">
                <Link
                    href="/"
                    className="inline-flex items-center gap-2 text-violet-600 hover:text-violet-700 mb-8"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Home
                </Link>

                <div className="max-w-2xl mx-auto">
                    <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-violet-600 to-purple-600 bg-clip-text text-transparent">
                        Generate Transcript
                    </h1>
                    <p className="text-lg text-gray-600 mb-10">
                        Paste a YouTube or Vimeo URL to get started
                    </p>

                    <form onSubmit={handleSubmit} className="space-y-6">
                        {/* URL Input */}
                        <div>
                            <label
                                htmlFor="url"
                                className="block text-sm font-semibold text-gray-700 mb-2"
                            >
                                Video URL
                            </label>
                            <input
                                id="url"
                                type="url"
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                                placeholder="https://youtube.com/watch?v=..."
                                className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-violet-500 focus:ring focus:ring-violet-200 outline-none transition-colors"
                                required
                            />
                        </div>

                        {/* Format Selection */}
                        <div>
                            <label className="block text-sm font-semibold text-gray-700 mb-3">
                                Transcript Format
                            </label>
                            <div className="grid grid-cols-3 gap-3">
                                {[
                                    { value: 'clean' as const, label: 'Clean Text' },
                                    { value: 'timestamp' as const, label: 'With Timestamps' },
                                    { value: 'paragraph' as const, label: 'Paragraphs' },
                                ].map((option) => (
                                    <button
                                        key={option.value}
                                        type="button"
                                        onClick={() => setFormat(option.value)}
                                        className={`px-4 py-3 rounded-xl font-medium transition-all ${format === option.value
                                            ? 'bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-lg'
                                            : 'bg-white border-2 border-gray-200 text-gray-700 hover:border-violet-300'
                                            }`}
                                    >
                                        {option.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* File Type Selection */}
                        <div>
                            <label className="block text-sm font-semibold text-gray-700 mb-3">
                                File Type
                            </label>
                            <div className="grid grid-cols-3 gap-3">
                                {[
                                    { value: 'txt' as const, label: 'TXT' },
                                    { value: 'docx' as const, label: 'DOCX' },
                                    { value: 'pdf' as const, label: 'PDF' },
                                ].map((option) => (
                                    <button
                                        key={option.value}
                                        type="button"
                                        onClick={() => setFileType(option.value)}
                                        className={`px-4 py-3 rounded-xl font-medium transition-all ${fileType === option.value
                                            ? 'bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-lg'
                                            : 'bg-white border-2 border-gray-200 text-gray-700 hover:border-violet-300'
                                            }`}
                                    >
                                        {option.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full px-6 py-4 bg-gradient-to-r from-violet-600 to-purple-600 text-white font-semibold rounded-xl hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Generating...
                                </>
                            ) : (
                                'Generate Transcript'
                            )}
                        </button>
                    </form>

                    {/* Error Message */}
                    {error && (
                        <div className="mt-6 p-4 bg-red-50 border-2 border-red-200 rounded-xl text-red-700">
                            {error}
                        </div>
                    )}

                    {/* Success / Download */}
                    {downloadUrl && metadata && (
                        <div className="mt-6 p-6 bg-white rounded-xl shadow-lg border-2 border-green-200">
                            <div className="flex items-center gap-3 mb-4 border-b pb-4">
                                <CheckCircle2 className="w-6 h-6 text-green-600" />
                                <h3 className="text-lg font-semibold text-gray-900">
                                    Transcript Ready!
                                </h3>
                            </div>

                            <div className="mb-6 space-y-2">
                                <p className="text-gray-700"><strong>Title:</strong> {metadata.title}</p>
                                <p className="text-gray-700"><strong>Words:</strong> {metadata.words.toLocaleString()}</p>
                                <p className="text-gray-700"><strong>Est Reading Time:</strong> {Math.ceil(metadata.time / 60)} min</p>
                            </div>

                            <a
                                href={downloadUrl}
                                download={`transcript.${fileType}`}
                                className="flex items-center justify-center gap-2 w-full px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-xl hover:shadow-lg transition-all"
                            >
                                <Download className="w-5 h-5" />
                                Download Transcript
                            </a>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
