'use client';

import { useTheme } from 'next-themes';
import { useHydrated } from '../lib/useHydrated';

export function ThemeToggle() {
    const { theme, setTheme } = useTheme();
    const mounted = useHydrated();

    if (!mounted) return <span className="w-16" />;

    const isDark = theme === 'dark';

    return (
        <button
            onClick={() => setTheme(isDark ? 'light' : 'dark')}
            className="text-xs font-medium px-3 py-1.5 rounded-md border transition-colors cursor-pointer"
            style={{
                borderColor: 'var(--border)',
                color: 'var(--muted)',
                background: 'var(--surface-2)',
            }}
            aria-label="Toggle theme"
        >
            {isDark ? '☀ Light' : '☾ Dark'}
        </button>
    );
}
