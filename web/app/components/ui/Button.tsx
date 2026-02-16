import React from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'glass';
    isLoading?: boolean;
    glow?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
    children,
    variant = 'primary',
    isLoading = false,
    glow = false,
    className = '',
    ...props
}) => {
    const baseStyles = "relative inline-flex items-center justify-center px-8 py-3 font-orbitron font-medium tracking-wider text-sm transition-all duration-300 rounded-sm overflow-hidden group";

    const variants = {
        primary: "bg-singularity text-black hover:bg-singularity-hover disabled:opacity-50 disabled:cursor-not-allowed",
        secondary: "bg-transparent border border-singularity text-singularity hover:bg-singularity/10",
        glass: "bg-white/5 border border-white/10 text-white hover:bg-white/10 backdrop-blur-md",
    };

    const glowEffect = glow ? "shadow-[0_0_20px_rgba(0,212,255,0.4)] hover:shadow-[0_0_30px_rgba(0,212,255,0.6)]" : "";

    return (
        <button
            className={`${baseStyles} ${variants[variant]} ${glowEffect} ${className}`}
            disabled={isLoading || props.disabled}
            {...props}
        >
            {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            <span className="relative z-10 flex items-center gap-2">
                {children}
            </span>

            {/* Hover Shine Effect */}
            <div className="absolute inset-0 -translate-x-full group-hover:animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/20 to-transparent z-0" />
        </button>
    );
};
