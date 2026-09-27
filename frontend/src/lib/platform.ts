"use client";

import { useEffect, useState } from "react";

/** Label for the platform's primary shortcut modifier. Starts as "Ctrl" on
 * the server and first client render (avoids a hydration mismatch), then
 * switches to "⌘" on Apple platforms after mount. */
export function useModKeyLabel(): string {
  const [label, setLabel] = useState("Ctrl");
  useEffect(() => {
    if (typeof navigator !== "undefined" && /Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent)) {
      setLabel("⌘");
    }
  }, []);
  return label;
}
