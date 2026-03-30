import { NextRequest, NextResponse } from "next/server";

function getRoleCookie(request: NextRequest): string | null {
  return request.cookies.get("atticus_role")?.value ?? null;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!pathname.startsWith("/admin") && !pathname.startsWith("/lawyer")) {
    return NextResponse.next();
  }

  const role = getRoleCookie(request);
  const allowedForPath = pathname.startsWith("/admin")
    ? new Set(["admin"])
    : new Set(["lawyer"]);

  if (!role || !allowedForPath.has(role)) {
    const url = request.nextUrl.clone();
    url.pathname = "/";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/lawyer/:path*"],
};
