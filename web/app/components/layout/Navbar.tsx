'use client';

import React from 'react';
import { Bot, Menu, X, Terminal } from 'lucide-react';

export const Navbar: React.FC = () => {
    const [isOpen, setIsOpen] = React.useState(false);

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-midnight/80 backdrop-blur-xl">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-20">

                    {/* Logo */}
                    <div className="flex-shrink-0 flex items-center gap-2 cursor-pointer group">
                        <div className="w-8 h-8 rounded bg-gradient-to-br from-singularity to-purple-600 flex items-center justify-center group-hover:shadow-[0_0_15px_rgba(0,212,255,0.5)] transition-all duration-300">
                            <Terminal className="text-white w-5 h-5" />
                        </div>
                        <span className="font-orbitron font-bold text-xl tracking-wider text-white">
                            TRANSCRIPT<span className="text-singularity">FLOW</span>
                        </span>
                    </div>

                    {/* Desktop Menu */}
                    <div className="hidden md:block">
                        <div className="ml-10 flex items-baseline space-x-8">
                            {['Features', 'API', 'Pricing', 'Roadmap'].map((item) => (
                                <a
                                    key={item}
                                    href={`#${item.toLowerCase()}`}
                                    className="font-sans text-sm font-medium text-gray-300 hover:text-singularity transition-colors duration-200"
                                >
                                    {item}
                                </a>
                            ))}
                        </div>
                    </div>

                    {/* CTA & Mobile Button */}
                    <div className="flex items-center gap-4">
                        <a
                            href="https://t.me/TranscriptFlowBot"
                            target="_blank"
                            rel="noreferrer"
                            className="hidden md:flex items-center gap-2 px-4 py-2 rounded border border-white/10 bg-white/5 hover:bg-white/10 transition-all font-orbitron text-xs text-singularity tracking-widest uppercase"
                        >
                            <Bot className="w-4 h-4" />
                            Open Telegram
                        </a>

                        <div className="-mr-2 flex md:hidden">
                            <button
                                onClick={() => setIsOpen(!isOpen)}
                                className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-white hover:bg-white/10 focus:outline-none"
                            >
                                {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Mobile Menu */}
            {isOpen && (
                <div className="md:hidden bg-black/90 backdrop-blur-xl border-b border-white/10">
                    <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3">
                        {['Features', 'API', 'Pricing', 'Roadmap'].map((item) => (
                            <a
                                key={item}
                                href={`#${item.toLowerCase()}`}
                                className="block px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:text-white hover:bg-white/10 font-orbitron"
                            >
                                {item}
                            </a>
                        ))}
                        <a
                            href="https://t.me/TranscriptFlowBot"
                            className="block w-full text-left px-3 py-2 text-singularity font-orbitron"
                        >
                            Launch Telegram Bot
                        </a>
                    </div>
                </div>
            )}
        </nav>
    );
};
