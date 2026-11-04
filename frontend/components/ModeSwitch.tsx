"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type Role, useIdentity } from "@/lib/identity";

// The page each role works in. Team members write in the chat; the dispatcher plans on the Dispatcher
// page and reads the chat there; a workshop reports its current state.
const MODES: Record<Role, { href: string; label: string }[]> = {
  team: [{ href: "/operations", label: "Chat" }],
  dispatcher: [{ href: "/dispatcher", label: "Dispatcher" }],
  workshop: [{ href: "/workshop", label: "Workshop" }],
};

// The signed-in role's page, one click away on every page. Nothing is shown before sign-in.
export default function ModeSwitch() {
  const pathname = usePathname();
  const identity = useIdentity();
  if (!identity) {
    return null;
  }
  return (
    <nav className="mode-switch" aria-label="Mode">
      {MODES[identity.role].map((mode) => (
        <Link key={mode.href} href={mode.href} aria-current={pathname === mode.href ? "page" : undefined}>
          {mode.label}
        </Link>
      ))}
    </nav>
  );
}
