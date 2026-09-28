import { useSyncExternalStore } from 'react';

const subscribe = () => () => {};

/**
 * False during SSR and the hydration render, true afterwards. Use it to gate UI
 * that depends on client-only state (e.g. the resolved next-themes theme)
 * without a setState-in-effect "mounted" flag.
 */
export function useHydrated(): boolean {
    return useSyncExternalStore(subscribe, () => true, () => false);
}
