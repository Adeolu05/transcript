/**
 * JSON-LD structured data for SEO.
 * Renders a <script type="application/ld+json"> tag.
 */
export function JsonLd({ data }: { data: Record<string, unknown> }) {
    return (
        <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
        />
    );
}
