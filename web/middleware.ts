import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
    const host = request.headers.get('host') || '';

    // Redirect vercel.app domains to the production domain.
    // We check for NODE_ENV === "production" and VERCEL_ENV === "production" 
    // to ensure preview deployments (which have VERCEL_ENV === "preview") are NOT redirected.
    if (
        process.env.NODE_ENV === 'production' &&
        process.env.VERCEL_ENV === 'production' &&
        host.endsWith('.vercel.app')
    ) {
        const url = request.nextUrl.clone();
        url.host = 'usetranscriptflow.com';
        url.protocol = 'https:';
        url.port = '';
        return NextResponse.redirect(url, 308);
    }

    return NextResponse.next();
}

export const config = {
    matcher: [
        // Match all paths except internal next static files and image optimization
        '/((?!_next/static|_next/image|favicon.ico).*)',
    ],
};
