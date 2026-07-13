'use client';

import React from 'react';
import { ArrowRight, PlayCircle } from 'lucide-react';
import { Button } from '../ui/Button';

interface HeroProps {
    onStart: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onStart }) => {
    return (
        <div className="relative pt-32 pb-16 sm:pt-40 sm:pb-24 overflow-hidden">

            {/* Background Decor */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full max-w-7xl pointer-events-none">
                <div className="absolute top-20 left-1/4 w-96 h-96 bg-singularity/20 rounded-full blur-[120px] opacity-20 animate-pulse-slow" />
                <div className="absolute bottom-20 right-1/4 w-64 h-64 bg-purple-600/20 rounded-full blur-[100px] opacity-20" />
            </div>

            <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center z-10">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-singularity/30 bg-singularity/5 text-singularity text-xs font-orbitron tracking-wider mb-8">
                    <span className="w-2 h-2 rounded-full bg-singularity animate-pulse"></span>
                    V1.0 ENGINE ONLINE
                </div>

                <h1 className="text-5xl sm:text-7xl font-orbitron font-black tracking-tight text-white mb-8 leading-tight">
                    EXTRACT. <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-singularity to-purple-500">
                        TRANSCRIBE.
                    </span> <br />
                    CONQUER.
                </h1>

                <p className="mt-4 max-w-2xl mx-auto text-xl text-gray-400 font-sans leading-relaxed">
                    The ultimate infrastructure for video-to-text conversion.
                    Process YouTube, Vimeo, and Audio instantly via our Web Dashboard or Telegram Bot.
                </p>

                <div className="mt-10 flex flex-col sm:flex-row justify-center gap-4">
                    <Button onClick={onStart} glow>
                        LAUNCH WEB APP <ArrowRight className="w-4 h-4" />
                    </Button>
                    <Button variant="glass">
                        <PlayCircle className="w-4 h-4 mr-2" /> WATCH DEMO
                    </Button>
                </div>

                {/* Stats Grid - Mini Glass Cards */}
                <div className="mt-20 grid grid-cols-2 gap-4 sm:grid-cols-4 max-w-4xl mx-auto">
                    {[
                        { label: 'Speed', value: '< 10s' },
                        { label: 'Accuracy', value: '99.8%' },
                        { label: 'Users', value: '2.5k+' },
                        { label: 'Uptime', value: '99.9%' }
                    ].map((stat, i) => (
                        <div key={i} className="p-4 rounded border border-white/5 bg-white/5 backdrop-blur-sm">
                            <div className="text-2xl font-orbitron font-bold text-white">{stat.value}</div>
                            <div className="text-xs text-gray-500 font-sans uppercase tracking-widest">{stat.label}</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};
