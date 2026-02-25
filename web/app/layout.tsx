import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Analytics } from "@vercel/analytics/next";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://usetranscriptflow.com"),
  title: {
    default: "Transcript Flow – YouTube & Vimeo Transcript Downloader",
    template: "%s – Transcript Flow",
  },
  description:
    "Extract and download YouTube and Vimeo transcripts. Preview before download. TXT, PDF, DOCX. No account required.",
  robots: { index: true, follow: true },
  alternates: { canonical: "/" },
  icons: {
    icon: "/favicon.ico",
    apple: "/brand/icon-180.png",
  },
  openGraph: {
    type: "website",
    siteName: "Transcript Flow",
    title: "YouTube & Vimeo Transcript Downloader",
    description:
      "Extract and download YouTube and Vimeo transcripts. Preview before download. TXT, PDF, DOCX. No account required.",
    url: "https://usetranscriptflow.com",
    images: [{ url: "/opengraph-image.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "YouTube & Vimeo Transcript Downloader",
    description:
      "Extract and download YouTube and Vimeo transcripts. Preview before download. TXT, PDF, DOCX.",
    images: ["/opengraph-image.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="manifest" href="/site.webmanifest" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Geist:wght@300;400;500;600;700&family=Instrument+Serif:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className={`${inter.variable} antialiased`}>
        <Providers>
          {children}
        </Providers>
        <Analytics />
      </body>
    </html>
  );
}
