import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Radar", template: "%s · Radar" },
  description: "Personal job intelligence and early-warning system"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
