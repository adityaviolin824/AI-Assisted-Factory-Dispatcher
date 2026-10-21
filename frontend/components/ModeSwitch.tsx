"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const MODES = [
  { href: "/operations", label: "Chat" },
  { href: "/dispatcher", label: "Dispatcher" },
];

// Chat and Dispatcher, one click apart on every page. It is navigation only: there is no login or role yet.
export default function ModeSwitch() {
  const pathname = usePathname();
  return (
    <nav className="mode-switch" aria-label="Mode">
      {MODES.map((mode) => (
        <Link key={mode.href} href={mode.href} aria-current={pathname === mode.href ? "page" : undefined}>
          {mode.label}
        </Link>
      ))}
    </nav>
  );
}
