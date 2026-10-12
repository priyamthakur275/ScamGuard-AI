import { NextResponse, type NextRequest } from "next/server";

// This is a fast, coarse gate only -- it checks whether a session COOKIE
// is present (set by token-storage.ts alongside the real access token in
// localStorage), not whether the actual JWT is still valid. That real
// check happens client-side in ProtectedRoute, which calls the backend
// and is the actual source of truth. This middleware exists purely to
// avoid a flash of a protected page's content before ProtectedRoute's
// effect has a chance to run, for the common case (no session at all).
const AUTH_PAGES = ["/login", "/register"];

/** Requests to the backend go through the /backend-api rewrite, so the
 * backend sees this Next.js server as the caller. Pass the browser's own
 * IP along explicitly so the backend's rate limits apply per visitor,
 * not to everyone sharing this one server. */
function forwardClientIp(request: NextRequest) {
  const forwarded = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const clientIp = forwarded || request.headers.get("x-real-ip") || request.ip || "";
  const headers = new Headers(request.headers);
  if (clientIp) headers.set("x-scamguard-client-ip", clientIp);
  return NextResponse.next({ request: { headers } });
}

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith("/backend-api/")) return forwardClientIp(request);

  const hasSessionCookie = request.cookies.has("has_session");
  const { pathname } = request.nextUrl;

  if (!hasSessionCookie && !AUTH_PAGES.includes(pathname)) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (hasSessionCookie && AUTH_PAGES.includes(pathname)) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/backend-api/:path*", "/dashboard/:path*", "/analyze/:path*", "/history/:path*", "/analytics/:path*", "/settings/:path*", "/admin/:path*", "/login", "/register"],
};
