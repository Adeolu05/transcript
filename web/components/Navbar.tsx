'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useTheme } from 'next-themes';
import { useHydrated } from '../lib/useHydrated';

interface NavbarProps {
    links: { label: string; href?: string; onClick?: () => void }[];
    showThemeToggle?: boolean;
}

export function Navbar({ links, showThemeToggle = false }: NavbarProps) {
    const [scrolled, setScrolled] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const { theme, setTheme } = useTheme();
    const mounted = useHydrated();

    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 8);
        onScroll();
        window.addEventListener('scroll', onScroll, { passive: true });
        return () => window.removeEventListener('scroll', onScroll);
    }, []);

    // Close menu on resize past mobile breakpoint
    useEffect(() => {
        const onResize = () => { if (window.innerWidth >= 640) setMenuOpen(false); };
        window.addEventListener('resize', onResize, { passive: true });
        return () => window.removeEventListener('resize', onResize);
    }, []);

    // Lock body scroll when menu is open
    useEffect(() => {
        document.body.style.overflow = menuOpen ? 'hidden' : '';
        return () => { document.body.style.overflow = ''; };
    }, [menuOpen]);

    const handleLinkClick = useCallback((link: { href?: string; onClick?: () => void }) => {
        setMenuOpen(false);
        if (link.onClick) link.onClick();
    }, []);

    return (
        <>
            <nav className={`navbar ${scrolled || menuOpen ? 'navbar--scrolled' : 'navbar--top'}`}>
                <div className="max-w-6xl mx-auto flex items-center justify-between px-4 py-4">
                    <Link
                        href="/"
                        className="hover:opacity-70 transition-opacity text-base font-semibold tracking-tighter"
                        style={{ color: 'var(--text)' }}
                    >
                        Transcript Flow
                    </Link>

                    {/* Desktop links */}
                    <div className="hidden sm:flex items-center gap-8 text-[10px] font-medium tracking-widest" style={{ color: 'var(--muted)' }}>
                        {links.map((link) =>
                            link.href ? (
                                link.href.startsWith('http') ? (
                                    <a key={link.label} href={link.href} target="_blank" rel="noopener noreferrer" className="hover:opacity-70 transition-opacity cursor-pointer">
                                        {link.label}
                                    </a>
                                ) : (
                                    <Link key={link.label} href={link.href} className="hover:opacity-70 transition-opacity cursor-pointer">
                                        {link.label}
                                    </Link>
                                )
                            ) : (
                                <button key={link.label} onClick={link.onClick} className="hover:opacity-70 transition-opacity cursor-pointer">
                                    {link.label}
                                </button>
                            )
                        )}
                        {showThemeToggle && mounted && (
                            <button
                                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                                className="flex items-center gap-2 px-3 py-1.5 rounded-full transition-all cursor-pointer text-[10px] font-bold tracking-widest uppercase"
                                style={{ border: '1px solid var(--border)', color: 'var(--muted)', background: 'var(--surface)' }}
                                aria-label="Toggle theme"
                            >
                                {theme === 'dark' ? '☀' : '☾'}
                                <span>{theme === 'dark' ? 'light' : 'dark'}</span>
                            </button>
                        )}
                    </div>

                    {/* Mobile: theme toggle + hamburger */}
                    <div className="flex sm:hidden items-center gap-3">
                        {showThemeToggle && mounted && (
                            <button
                                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                                className="w-8 h-8 flex items-center justify-center rounded-full cursor-pointer"
                                style={{ border: '1px solid var(--border)', color: 'var(--muted)' }}
                                aria-label="Toggle theme"
                            >
                                <span className="text-sm">{theme === 'dark' ? '☀' : '☾'}</span>
                            </button>
                        )}
                        <button
                            onClick={() => setMenuOpen(!menuOpen)}
                            className="w-8 h-8 flex flex-col items-center justify-center gap-[5px] cursor-pointer"
                            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
                            style={{ color: 'var(--text)' }}
                        >
                            <span
                                className="block w-[18px] h-[1.5px] rounded-full transition-all duration-200"
                                style={{
                                    background: 'var(--text)',
                                    transform: menuOpen ? 'translateY(3.25px) rotate(45deg)' : 'none',
                                }}
                            />
                            <span
                                className="block w-[18px] h-[1.5px] rounded-full transition-all duration-200"
                                style={{
                                    background: 'var(--text)',
                                    opacity: menuOpen ? 0 : 1,
                                }}
                            />
                            <span
                                className="block w-[18px] h-[1.5px] rounded-full transition-all duration-200"
                                style={{
                                    background: 'var(--text)',
                                    transform: menuOpen ? 'translateY(-3.25px) rotate(-45deg)' : 'none',
                                }}
                            />
                        </button>
                    </div>
                </div>
            </nav>

            {/* Mobile menu overlay */}
            {menuOpen && (
                <div
                    className="fixed inset-0 z-40 flex flex-col pt-20 px-6 pb-8 sm:hidden"
                    style={{ background: 'var(--bg)' }}
                >
                    <div className="flex flex-col gap-1 flex-grow">
                        {links.map((link) =>
                            link.href ? (
                                link.href.startsWith('http') ? (
                                    <a
                                        key={link.label}
                                        href={link.href}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        onClick={() => setMenuOpen(false)}
                                        className="block py-3 text-lg font-medium lowercase tracking-wide transition-opacity hover:opacity-70"
                                        style={{ color: 'var(--text)', borderBottom: '1px solid var(--border)' }}
                                    >
                                        {link.label}
                                    </a>
                                ) : (
                                    <Link
                                        key={link.label}
                                        href={link.href}
                                        onClick={() => setMenuOpen(false)}
                                        className="block py-3 text-lg font-medium lowercase tracking-wide transition-opacity hover:opacity-70"
                                        style={{ color: 'var(--text)', borderBottom: '1px solid var(--border)' }}
                                    >
                                        {link.label}
                                    </Link>
                                )
                            ) : (
                                <button
                                    key={link.label}
                                    onClick={() => handleLinkClick(link)}
                                    className="block py-3 text-lg font-medium lowercase tracking-wide text-left transition-opacity hover:opacity-70 cursor-pointer"
                                    style={{ color: 'var(--text)', borderBottom: '1px solid var(--border)' }}
                                >
                                    {link.label}
                                </button>
                            )
                        )}
                    </div>
                    <span className="text-[10px] font-semibold uppercase tracking-[0.4em] mt-auto" style={{ color: 'var(--muted)' }}>
                        © 2026 Transcript Flow
                    </span>
                </div>
            )}
        </>
    );
}
