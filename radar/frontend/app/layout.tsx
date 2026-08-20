import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Radar — Focused job alerts", template: "%s · Radar" },
  description: "Radar finds relevant jobs across company career sources and broader job feeds, then brings them into one simple workspace."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" suppressHydrationWarning><body>{children}</body></html>;
}
