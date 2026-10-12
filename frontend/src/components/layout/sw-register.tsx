"use client";

import { useEffect } from "react";

/** Registers public/sw.js so ScamGuard can be installed (and receive shares on Android). */
export function ServiceWorkerRegister() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* installability is a bonus; never break the page over it */
    });
  }, []);
  return null;
}
