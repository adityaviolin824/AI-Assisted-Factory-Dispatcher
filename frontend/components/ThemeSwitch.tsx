"use client";

import { useSyncExternalStore } from "react";

// The browser remembers the choice in localStorage under this key. The script in app/layout.tsx
// reads the same key before the page is drawn, so a light page does not flash dark first.
const THEME_KEY = "theme";

// The theme is the data-theme attribute on <html>; globals.css changes its colours when it is "light".
function isLight() {
  return document.documentElement.dataset.theme === "light";
}

// Tells React whenever the attribute changes, so the switch always shows the theme on screen.
function watchTheme(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

// Light mode on or off, on every page. Dark is the default. Only colours change, nothing else.
export default function ThemeSwitch() {
  // The server cannot see the browser's choice, so the server-drawn switch is off (dark).
  const light = useSyncExternalStore(watchTheme, isLight, () => false);

  function toggle() {
    const theme = light ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }

  return (
    <button type="button" role="switch" aria-checked={light} className="theme-switch" onClick={toggle}>
      <span className="track" aria-hidden="true" />
      Light mode
    </button>
  );
}
