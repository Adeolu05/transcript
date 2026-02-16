import React from 'react';
import { Terminal, Github, Twitter } from 'lucide-react';

export const Footer: React.FC = () => {
    return (
        <footer className="border-t border-white/10 bg-black py-12">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex flex-col md:flex-row justify-between items-center gap-8">

                    <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded bg-singularity/20 flex items-center justify-center">
                            <Terminal className="text-singularity w-3 h-3" />
                        </div>
                        <span className="font-orbitron font-bold text-lg tracking-wider text-white">
                            TRANSCRIPT<span className="text-singularity">FLOW</span>
                        </span>
                    </div>

                    <div className="flex items-center gap-6">
                        <a href="#" className="text-gray-500 hover:text-white transition-colors"><Github className="w-5 h-5" /></a>
                        <a href="#" className="text-gray-500 hover:text-white transition-colors"><Twitter className="w-5 h-5" /></a>
                    </div>

                    <div className="text-xs text-gray-600 font-sans">
                        © 2026 TranscriptFlow. Infrastructure for the AI Age.
                    </div>
                </div>
            </div>
        </footer>
    );
};
