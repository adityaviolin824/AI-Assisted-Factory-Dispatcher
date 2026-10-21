import type { Metadata } from "next";
import { Archivo, Literata } from "next/font/google";
import Link from "next/link";
import ModeSwitch from "@/components/ModeSwitch";
import "./globals.css";

// Archivo labels and calculated values; its width axis gives the expanded headings (DESIGN.md).
const archivo = Archivo({ subsets: ["latin"], axes: ["wdth"], variable: "--font-archivo" });
// Literata is kept for words a person wrote: chat messages and quoted source messages.
const literata = Literata({ subsets: ["latin"], axes: ["opsz"], variable: "--font-literata" });

export const metadata: Metadata = {
  title: "Workshop dispatch",
  description: "Factory chat requests, Python-calculated workshop allocations and the dispatcher's review.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${archivo.variable} ${literata.variable}`}>
      <body>
        <header className="app-bar">
          <span className="brand">Workshop dispatch</span>
          <ModeSwitch />
          <Link href="/" className="about-link">
            About
          </Link>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
