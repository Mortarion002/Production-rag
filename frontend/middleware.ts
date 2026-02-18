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
  if (pathname === "/login" || pathname === "/signup") {
    if (token) {
      // Optimistically verify, if valid, redirect to chat
      try {
        await jwtVerify(token, SECRET_KEY);
        return NextResponse.redirect(new URL("/chat", request.url));
      } catch (e) {
        // Invalid token, stay on login
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
        // Redirect unauthorized users to chat or 403
        return NextResponse.rewrite(new URL("/403", request.url));
        // Or redirect: return NextResponse.redirect(new URL('/chat', request.url))
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
