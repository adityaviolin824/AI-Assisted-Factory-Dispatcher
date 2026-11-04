import { useMemo, useSyncExternalStore } from "react";

export type Role = "team" | "dispatcher" | "workshop";
// A workshop's person also names the workshop they report for (3 November 2026).
export type Identity = { name: string; role: Role; workshopId?: string; workshopName?: string };

export const ROLE_LABELS: Record<Role, string> = { team: "Team member", dispatcher: "Dispatcher", workshop: "Workshop" };

// Each role works on one page: team members write in the chat, the dispatcher plans on the Dispatcher
// page, where they can read the chat but not change it, and a workshop reports its current state.
export const HOME_PAGE: Record<Role, string> = { team: "/operations", dispatcher: "/dispatcher", workshop: "/workshop" };

// The signed-in name and role, remembered for this browser tab only, so one laptop can show a team
// member tab and a dispatcher tab side by side. It is a label for the demo, not an account: there is
// no password and the backend does not check it.
const IDENTITY_KEY = "identity";
// The browser tells other tabs about a sessionStorage change, but not the tab that made it, so
// signing in and out announce the change to this tab themselves.
const CHANGED = "identity-changed";

/** Return why a name cannot be used, or null if it can. Matches the backend's rule for a chat
 * sender, because a snapshot line reads "R01 [08:08] Name: text". */
export function nameProblem(name: string): string | null {
  if (name.trim() === "") {
    return "Enter your name.";
  }
  if (name.includes(":")) {
    return "Use a name without a colon.";
  }
  return null;
}

export function signIn(identity: Identity) {
  sessionStorage.setItem(IDENTITY_KEY, JSON.stringify({ ...identity, name: identity.name.trim() }));
  window.dispatchEvent(new Event(CHANGED));
}

export function signOut() {
  sessionStorage.removeItem(IDENTITY_KEY);
  window.dispatchEvent(new Event(CHANGED));
}

function watchIdentity(onChange: () => void) {
  window.addEventListener(CHANGED, onChange);
  return () => window.removeEventListener(CHANGED, onChange);
}

/** The signed-in identity: null when nobody has signed in in this tab, and undefined while the page is
 * drawn on the server, where sessionStorage does not exist. */
export function useIdentity(): Identity | null | undefined {
  const saved = useSyncExternalStore(watchIdentity, () => sessionStorage.getItem(IDENTITY_KEY), () => undefined);
  // Parsed once per saved value, so components can compare identities between renders.
  return useMemo(() => (typeof saved === "string" ? (JSON.parse(saved) as Identity) : saved), [saved]);
}
