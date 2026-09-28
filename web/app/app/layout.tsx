import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Transcript Extractor",
    description:
        "Paste a link, preview transcript, then download as TXT, PDF, DOCX, SRT, or VTT.",
    alternates: { canonical: "/app" },
    openGraph: {
        title: "Transcript Extractor",
        description:
            "Paste a link, preview transcript, then download as TXT, PDF, DOCX, SRT, or VTT.",
        url: "https://usetranscriptflow.com/app",
    },
};

export default function AppLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <>{children}</>;
}
