'use client';

import React, { useEffect, useState } from 'react';
import { Bot, Send, FileText, Check, MoreVertical } from 'lucide-react';

interface Message {
    id: number;
    text: string;
    sender: 'user' | 'bot';
    file?: boolean;
}

export const BotDemo: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([]);

    // Auto-play chat sequence
    useEffect(() => {
        const sequence = [
            { delay: 1000, msg: { id: 1, text: "/start", sender: 'user' as const } },
            { delay: 2000, msg: { id: 2, text: "Transcript Flow\nSend me a YouTube or Vimeo link.", sender: 'bot' as const } },
            { delay: 4000, msg: { id: 3, text: "https://youtu.be/dQw4w9WgXcQ", sender: 'user' as const } },
            { delay: 5000, msg: { id: 4, text: "Extracting transcript...", sender: 'bot' as const } },
            { delay: 7500, msg: { id: 5, text: "Transcript ready:", sender: 'bot' as const, file: true } },
        ];

        let timeouts: ReturnType<typeof setTimeout>[] = [];

        const runSequence = () => {
            setMessages([]);

            sequence.forEach(({ delay, msg }) => {
                const timeout = setTimeout(() => {
                    setMessages(prev => [...prev, msg]);
                }, delay);
                timeouts.push(timeout);
            });

            // Loop
            const resetTimeout = setTimeout(runSequence, 12000);
            timeouts.push(resetTimeout);
        };

        runSequence();

        return () => timeouts.forEach(clearTimeout);
    }, []);

    return (
        <section className="py-12 relative overflow-hidden">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">

                    {/* Left Content */}
                    <div className="space-y-10">
                        <h2 className="text-4xl md:text-5xl font-bold leading-tight" style={{ color: 'var(--text)' }}>
                            <span style={{ color: 'var(--link)' }}>Use via</span> Telegram
                        </h2>
                        <p className="text-lg leading-relaxed" style={{ color: 'var(--muted)' }}>
                            Send a link. Choose your format. Get the transcript back as a file.
                        </p>

                        <ul className="space-y-5">
                            {[
                                'YouTube and Vimeo links',
                                'TXT, PDF, DOCX',
                                'Optional timestamps',
                                'Preview before download'
                            ].map((item, i) => (
                                <li key={i} className="flex items-center gap-3" style={{ color: 'var(--muted)' }}>
                                    <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{ background: 'rgba(46,92,158,0.1)' }}>
                                        <Check className="w-3 h-3" style={{ color: 'var(--link)' }} />
                                    </div>
                                    {item}
                                </li>
                            ))}
                        </ul>

                        <button
                            onClick={() => window.open('https://t.me/TranscriptFlowBot', '_blank')}
                            className="inline-flex items-center gap-2 px-6 py-3 rounded-full text-white text-sm font-semibold tracking-wide transition-opacity hover:opacity-90 cursor-pointer"
                            style={{ background: 'var(--primary)' }}
                        >
                            <Bot className="w-4 h-4" /> Open Bot
                        </button>
                    </div>

                    {/* Right: Phone Simulation */}
                    <div className="relative mx-auto lg:mr-0 max-w-[360px] w-full">
                        {/* Phone Bezel */}
                        <div className="relative z-10 overflow-hidden h-[650px] rounded-[3rem]"
                            style={{ background: 'var(--surface)', border: '3px solid var(--border)' }}>

                            {/* Telegram Header */}
                            <div className="p-4 flex items-center justify-between" style={{ background: 'var(--surface-2)', borderBottom: '1px solid var(--border)' }}>
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-white"
                                        style={{ background: 'var(--primary)' }}>
                                        <Bot className="w-6 h-6" />
                                    </div>
                                    <div>
                                        <div className="font-sans font-semibold text-sm" style={{ color: 'var(--text)' }}>Transcript Flow Bot</div>
                                        <div className="text-xs" style={{ color: 'var(--link)' }}>bot</div>
                                    </div>
                                </div>
                                <MoreVertical className="w-5 h-5" style={{ color: 'var(--muted)' }} />
                            </div>

                            {/* Chat Area */}
                            <div className="h-full p-4 space-y-4 overflow-y-auto pb-24" style={{ background: 'var(--bg)' }}>
                                {messages.map((msg) => (
                                    <div
                                        key={msg.id}
                                        className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}
                                    >
                                        <div className={`max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed ${msg.sender === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'}`}
                                            style={msg.sender === 'user'
                                                ? { background: 'var(--primary)', color: '#fff' }
                                                : { background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border)' }
                                            }>
                                            {msg.text}

                                            {msg.file && (
                                                <div className="mt-2 flex items-center gap-3 p-2 rounded lg:min-w-[180px]"
                                                    style={{ background: 'rgba(0,0,0,0.08)' }}>
                                                    <div className="w-8 h-8 rounded flex items-center justify-center" style={{ background: 'rgba(220,38,38,0.1)', color: 'var(--danger)' }}>
                                                        <FileText className="w-4 h-4" />
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="truncate font-medium text-xs" style={{ color: 'var(--text)' }}>transcript_2026.txt</div>
                                                        <div className="text-[10px]" style={{ color: 'var(--muted)' }}>14 KB</div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Input Area */}
                            <div className="absolute bottom-0 w-full p-4" style={{ background: 'var(--surface)', borderTop: '1px solid var(--border)' }}>
                                <div className="flex items-center gap-2">
                                    <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                                        <span className="text-lg" style={{ color: 'var(--muted)' }}>+</span>
                                    </div>
                                    <div className="flex-1 rounded-full h-8 px-3 text-xs flex items-center" style={{ background: 'var(--bg)', color: 'var(--muted)', border: '1px solid var(--border)' }}>
                                        Write a message...
                                    </div>
                                    <Send className="w-5 h-5" style={{ color: 'var(--link)' }} />
                                </div>
                            </div>

                        </div>


                    </div>

                </div>
            </div>
        </section>
    );
};
