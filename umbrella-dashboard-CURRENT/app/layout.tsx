import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "UmbrellaOS",
  description: "UmbrellaOS unified experience layer",
};

// Root layout stays a server component (Decision 6 / scoping doc's
// performance constraint) — nothing interactive lives here.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
