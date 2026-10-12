"use client";

import { useEffect } from "react";

/**
 * Fires one lightweight health request as soon as a public page (landing,
 * sign in, register) is shown. On a free hosting plan the API server sleeps
 * when idle and needs several seconds to start; this lets it start while
 * the person is still reading or typing, instead of after they press
 * "Sign in". The request does no database work and its result is ignored.
 */
export function BackendWarmup() {
  useEffect(() => {
    const controller = new AbortController();
    fetch("/backend-api/api/v1/health", { cache: "no-store", signal: controller.signal }).catch(() => {});
    return () => controller.abort();
  }, []);
  return null;
}
