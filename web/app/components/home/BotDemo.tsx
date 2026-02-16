'use client';

import React, { useEffect, useState } from 'react';
import { Bot, Send, FileText, Check, MoreVertical } from 'lucide-react';
import { Button } from '../ui/Button';

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
            { delay: 2000, msg: { id: 2, text: "TranscriptFlow Engine Online ⚡\nSend me a YouTube link.", sender: 'bot' as const } },
            { delay: 4000, msg: { id: 3, text: "https://youtu.be/dQw4w9WgXcQ", sender: 'user' as const } },
            { delay: 5000, msg: { id: 4, text: "Processing video ID: dQw4w9WgXcQ...", sender: 'bot' as const } },
            { delay: 7500, msg: { id: 5, text: "Transcript Ready:", sender: 'bot' as const, file: true } },
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
        <section className="py-24 relative overflow-hidden">
            {/* Ambient Background */}
            <div className="absolute top-1/2 left-0 -translate-y-1/2 w-96 h-96 bg-singularity/10 rounded-full blur-[100px] -z-10" />

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">

                    {/* Left Content */}
                    <div className="space-y-8">
                        <h2 className="text-4xl md:text-5xl font-orbitron font-bold leading-tight">
                            Native <span className="text-singularity">Telegram</span> Integration
                        </h2>
                        <p className="text-gray-400 text-lg leading-relaxed">
                            Experience the power of TranscriptFlow without leaving your favorite messenger.
                            Our bot runs on a globally distributed edge network, delivering parsed transcripts, summaries, and repurposing data in seconds.
                        </p>

                        <ul className="space-y-4">
                            {[
                                'Instant URL Detection',
                                'PDF & DOCX Export',
                                'AI Summarization (Pro)',
                                'Playlist Batching'
                            ].map((item, i) => (
                                <li key={i} className="flex items-center gap-3 text-gray-300">
                                    <div className="w-6 h-6 rounded-full bg-singularity/10 flex items-center justify-center">
                                        <Check className="w-3 h-3 text-singularity" />
                                    </div>
                                    {item}
                                </li>
                            ))}
                        </ul>

                        <Button onClick={() => window.open('https://t.me/TranscriptFlowBot', '_blank')} glow>
                            <Bot className="w-4 h-4 mr-2" /> START BOT
                        </Button>
                    </div>

                    {/* Right: Phone Simulation */}
                    <div className="relative mx-auto lg:mr-0 max-w-[360px] w-full">
                        {/* Phone Bezel */}
                        <div className="relative z-10 bg-midnight border-4 border-white/10 rounded-[3rem] shadow-2xl shadow-singularity/20 overflow-hidden h-[650px]">

                            {/* Telegram Header */}
                            <div className="bg-[#1c1c1c] p-4 flex items-center justify-between border-b border-white/5">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-singularity to-blue-600 flex items-center justify-center text-white">
                                        <Bot className="w-6 h-6" />
                                    </div>
                                    <div>
                                        <div className="font-sans font-semibold text-white text-sm">TranscriptFlow Bot</div>
                                        <div className="text-singularity text-xs">bot</div>
                                    </div>
                                </div>
                                <MoreVertical className="text-gray-500 w-5 h-5" />
                            </div>

                            {/* Chat Area */}
                            <div className="bg-[#0f0f0f] h-full p-4 space-y-4 overflow-y-auto pb-24">
                                {messages.map((msg) => (
                                    <div
                                        key={msg.id}
                                        className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}
                                    >
                                        <div className={`max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed ${msg.sender === 'user'
                                                ? 'bg-singularity text-black rounded-tr-sm'
                                                : 'bg-[#212121] text-white rounded-tl-sm'
                                            }`}>
                                            {msg.text}

                                            {msg.file && (
                                                <div className="mt-2 flex items-center gap-3 bg-black/20 p-2 rounded lg:min-w-[180px]">
                                                    <div className="w-8 h-8 bg-red-500/20 rounded flex items-center justify-center text-red-400">
                                                        <FileText className="w-4 h-4" />
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="truncate font-medium text-xs">transcript_2026.txt</div>
                                                        <div className="text-[10px] text-gray-400">14 KB</div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Input Area */}
                            <div className="absolute bottom-0 w-full bg-[#1c1c1c] p-4 border-t border-white/5">
                                <div className="flex items-center gap-2">
                                    <div className="w-8 h-8 rounded-full bg-[#2c2c2c] flex items-center justify-center">
                                        <span className="text-gray-500 text-lg">+</span>
                                    </div>
                                    <div className="flex-1 bg-black rounded-full h-8 px-3 text-xs flex items-center text-gray-500">
                                        Write a message...
                                    </div>
                                    <Send className="text-singularity w-5 h-5" />
                                </div>
                            </div>

                        </div>

                        {/* Glow Behind Phone */}
                        <div className="absolute -inset-4 bg-singularity/20 blur-3xl -z-10 rounded-[3rem]" />
                    </div>

                </div>
            </div>
        </section>
    );
};
