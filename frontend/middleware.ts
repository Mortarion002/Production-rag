import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { jwtVerify } from "jose";

const SECRET_KEY = new TextEncoder().encode(
  process.env.SECRET_KEY || "your-secret-key-change-me-in-production",
);

export async function middleware(request: NextRequest) {
  const token = request.cookies.get("token")?.value;
  const { pathname } = request.nextUrl;

  // 1. Bypass public routes
  if (pathname === "/" || pathname === "/login" || pathname === "/signup") {
    if (token) {
      // Optimistically verify, if valid, redirect to dashboard
      try {
        await jwtVerify(token, SECRET_KEY);
        // If user is already logged in, redirect to dashboard
        return NextResponse.redirect(new URL("/dashboard", request.url));
      } catch (e) {
        // Invalid token, allow access to public routes (will likely need to login again)
      }
    }
    return NextResponse.next();
  }

  // 2. Protect protected routes
  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  try {
    const { payload } = await jwtVerify(token, SECRET_KEY);
    const role = payload.role as string;

    // 3. Role-based protection
    if (pathname.startsWith("/admin")) {
      if (role !== "admin") {
        // Redirect unauthorized users to dashboard
        return NextResponse.redirect(new URL('/dashboard', request.url))
      }
    }

    return NextResponse.next();
  } catch (error) {
    // Token invalid or expired
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.cookies.delete("token");
    return response;
  }
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
