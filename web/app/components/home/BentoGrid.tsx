import React from 'react';
import { Zap, Lock, Globe, Database, Bot, Share2 } from 'lucide-react';

export const BentoGrid: React.FC = () => {
    return (
        <div id="features" className="py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
                <h2 className="text-3xl font-orbitron font-bold text-white">System Architecture</h2>
                <p className="mt-4 text-gray-400">Built for scale. Designed for speed.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 auto-rows-[200px]">

                {/* Large Card: Telegram Bot */}
                <div className="md:col-span-2 md:row-span-2 rounded-xl p-8 border border-white/10 bg-gradient-to-br from-white/5 to-transparent backdrop-blur-md relative group overflow-hidden">
                    <div className="absolute top-0 right-0 p-6 opacity-20 group-hover:opacity-40 transition-opacity">
                        <Bot className="w-32 h-32 text-singularity" />
                    </div>
                    <div className="relative z-10 h-full flex flex-col justify-end">
                        <div className="w-12 h-12 rounded-lg bg-singularity/10 flex items-center justify-center mb-4 text-singularity border border-singularity/20">
                            <Bot className="w-6 h-6" />
                        </div>
                        <h3 className="text-2xl font-orbitron font-bold text-white mb-2">Telegram Native</h3>
                        <p className="text-gray-400 text-sm leading-relaxed">
                            Don't leave your messenger. Send a link to <span className="text-singularity">@TranscriptFlowBot</span> and receive your file instantly. The core engine runs 24/7 on our distributed infrastructure.
                        </p>
                    </div>
                </div>

                {/* Card: Speed */}
                <div className="md:col-span-1 rounded-xl p-6 border border-white/10 bg-white/5 hover:bg-white/10 transition-colors backdrop-blur-md flex flex-col justify-between group">
                    <Zap className="w-8 h-8 text-yellow-400 group-hover:scale-110 transition-transform" />
                    <div>
                        <h4 className="text-lg font-orbitron font-semibold text-white">Lightning Fast</h4>
                        <p className="text-xs text-gray-500 mt-2">1-hour video processed in under 10 seconds.</p>
                    </div>
                </div>

                {/* Card: Security */}
                <div className="md:col-span-1 rounded-xl p-6 border border-white/10 bg-white/5 hover:bg-white/10 transition-colors backdrop-blur-md flex flex-col justify-between group">
                    <Lock className="w-8 h-8 text-green-400 group-hover:scale-110 transition-transform" />
                    <div>
                        <h4 className="text-lg font-orbitron font-semibold text-white">Secure Core</h4>
                        <p className="text-xs text-gray-500 mt-2">No permanent storage of processed data.</p>
                    </div>
                </div>

                {/* Medium Card: AI Ready */}
                <div className="md:col-span-2 rounded-xl p-6 border border-white/10 bg-gradient-to-r from-purple-900/20 to-blue-900/20 backdrop-blur-md flex flex-col justify-center relative overflow-hidden">
                    <div className="relative z-10 flex items-start gap-4">
                        <div className="p-3 rounded-full bg-white/10">
                            <Database className="w-6 h-6 text-purple-400" />
                        </div>
                        <div>
                            <h4 className="text-xl font-orbitron font-bold text-white">AI-Ready Output</h4>
                            <p className="text-sm text-gray-400 mt-2">
                                We generate cleaner data than raw captions. Perfect for feeding into GPT-4, Claude, or Llama for summarization and repurposing.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Card: Multi-Format */}
                <div className="md:col-span-1 rounded-xl p-6 border border-white/10 bg-white/5 hover:bg-white/10 transition-colors backdrop-blur-md flex flex-col justify-between group">
                    <Share2 className="w-8 h-8 text-pink-400 group-hover:scale-110 transition-transform" />
                    <div>
                        <h4 className="text-lg font-orbitron font-semibold text-white">Multi-Format</h4>
                        <p className="text-xs text-gray-500 mt-2">TXT, PDF, DOCX, SRT, VTT. Your choice.</p>
                    </div>
                </div>

                {/* Card: Global */}
                <div className="md:col-span-1 rounded-xl p-6 border border-white/10 bg-white/5 hover:bg-white/10 transition-colors backdrop-blur-md flex flex-col justify-between group">
                    <Globe className="w-8 h-8 text-blue-400 group-hover:scale-110 transition-transform" />
                    <div>
                        <h4 className="text-lg font-orbitron font-semibold text-white">Multi-Platform</h4>
                        <p className="text-xs text-gray-500 mt-2">YouTube & Vimeo supported. Auto-detects languages.</p>
                    </div>
                </div>

            </div>
        </div>
    );
};
