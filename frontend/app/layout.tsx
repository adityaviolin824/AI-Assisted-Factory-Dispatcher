import type { Metadata } from "next";
import { Archivo, Literata } from "next/font/google";
import Link from "next/link";
import ModeSwitch from "@/components/ModeSwitch";
import ThemeSwitch from "@/components/ThemeSwitch";
import "./globals.css";

// Archivo labels and calculated values; its width axis gives the expanded headings (DESIGN.md).
const archivo = Archivo({ subsets: ["latin"], axes: ["wdth"], variable: "--font-archivo" });
// Literata is kept for words a person wrote: chat messages and quoted source messages.
const literata = Literata({ subsets: ["latin"], axes: ["opsz"], variable: "--font-literata" });

export const metadata: Metadata = {
  title: "Workshop dispatch",
  description: "Factory chat requests, Python-calculated workshop allocations and the dispatcher's review.",
};

// Runs while the page loads, before anything is drawn: applies light mode if ThemeSwitch saved it
// (same "theme" key), so a light page never flashes dark. From the Next.js guide "How to prevent
// flash before hydration"; try/catch keeps the page working where the browser blocks localStorage.
const APPLY_SAVED_THEME = `try{if(localStorage.getItem("theme")==="light")document.documentElement.dataset.theme="light"}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning: the script above may add data-theme before React starts, which is expected.
    <html lang="en" className={`${archivo.variable} ${literata.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: APPLY_SAVED_THEME }} />
      </head>
      <body>
        <header className="app-bar">
          <span className="brand">Workshop dispatch</span>
          <ModeSwitch />
          <Link href="/" className="about-link">
            About
          </Link>
          <ThemeSwitch />
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
