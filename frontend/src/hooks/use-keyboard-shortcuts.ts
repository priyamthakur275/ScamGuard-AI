"use client";

import { useEffect } from "react";

type ShortcutHandler = (e: KeyboardEvent) => void;

interface ShortcutMap {
  [key: string]: ShortcutHandler;
}

export function useKeyboardShortcuts(shortcuts: ShortcutMap) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Create a string representation of the shortcut
      const keys = [];
      if (e.ctrlKey || e.metaKey) keys.push("mod");
      if (e.shiftKey) keys.push("shift");
      if (e.altKey) keys.push("alt");
      
      const key = e.key.toLowerCase();
      if (key !== "control" && key !== "meta" && key !== "shift" && key !== "alt") {
        keys.push(key);
      }
      
      const shortcutStr = keys.join("+");
      
      if (shortcuts[shortcutStr]) {
        shortcuts[shortcutStr](e);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [shortcuts]);
}
