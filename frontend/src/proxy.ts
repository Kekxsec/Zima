import { NextRequest, NextResponse } from "next/server"

const AUTH_COOKIE = "zima_session"

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/findings",
  "/scans",
  "/scores",
  "/signals",
  "/accounts",
  "/account",
  "/onboarding",
  "/connect-extension",
]

/** Only allow relative same-origin redirects — rejects external URLs */
export function sanitizeNext(next: string | null): string {
  if (!next) return "/dashboard"
  // Must start with "/" but not "//" (protocol-relative external URL)
  if (next.startsWith("/") && !next.startsWith("//") && !next.includes("://")) {
    return next
  }
  return "/dashboard"
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const isProtected = PROTECTED_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  )

  if (!isProtected) return NextResponse.next()

  const session = request.cookies.get(AUTH_COOKIE)
  if (!session?.value) {
    const signIn = new URL("/sign-in", request.url)
    signIn.searchParams.set("next", pathname)
    return NextResponse.redirect(signIn)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
}
