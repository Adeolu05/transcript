import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Transcript Flow - YouTube and Vimeo transcript downloader";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

export default function TwitterImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "56px",
          background:
            "linear-gradient(135deg, rgb(8, 12, 22) 0%, rgb(23, 36, 74) 55%, rgb(53, 104, 227) 100%)",
          color: "white",
          fontFamily: "Inter, Arial, sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            fontSize: "24px",
            opacity: 0.9,
          }}
        >
          <div
            style={{
              width: "16px",
              height: "16px",
              borderRadius: "9999px",
              background: "rgb(129, 196, 255)",
            }}
          />
          Transcript Flow
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div style={{ fontSize: "66px", lineHeight: 1.05, fontWeight: 800, letterSpacing: "-1.5px" }}>
            YouTube & Vimeo
            <br />
            Transcript Downloader
          </div>
          <div style={{ fontSize: "30px", opacity: 0.92 }}>
            Paste a link. Get a clean transcript in seconds.
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px", fontSize: "22px", opacity: 0.9 }}>
          <span>TXT</span>
          <span>•</span>
          <span>PDF</span>
          <span>•</span>
          <span>DOCX</span>
        </div>
      </div>
    ),
    size
  );
}
