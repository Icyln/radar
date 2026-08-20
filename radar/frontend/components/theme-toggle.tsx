"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "radar-workspace-theme";

type Theme = "light" | "dark";

function readTheme(): Theme {
  if (typeof window === "undefined") return "light";
  return window.localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
}

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    setTheme(readTheme());
  }, []);

  function apply(next: Theme) {
    setTheme(next);
    document.documentElement.dataset.workspaceTheme = next;
    window.localStorage.setItem(STORAGE_KEY, next);
  }

  return (
    <button
      type="button"
      className="button-secondary"
      onClick={() => apply(theme === "dark" ? "light" : "dark")}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {compact ? (theme === "dark" ? "Light" : "Dark") : `${theme === "dark" ? "Light" : "Dark"} mode`}
    </button>
  );
}
