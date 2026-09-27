import { NextResponse, type NextRequest } from "next/server";

// This is a fast, coarse gate only -- it checks whether a session COOKIE
// is present (set by token-storage.ts alongside the real access token in
// localStorage), not whether the actual JWT is still valid. That real
// check happens client-side in ProtectedRoute, which calls the backend
// and is the actual source of truth. This middleware exists purely to
// avoid a flash of a protected page's content before ProtectedRoute's
// effect has a chance to run, for the common case (no session at all).
const AUTH_PAGES = ["/login", "/register"];

export function middleware(request: NextRequest) {
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
  matcher: ["/dashboard/:path*", "/analyze/:path*", "/history/:path*", "/analytics/:path*", "/settings/:path*", "/admin/:path*", "/cases/:path*", "/demo/:path*", "/login", "/register"],
};
