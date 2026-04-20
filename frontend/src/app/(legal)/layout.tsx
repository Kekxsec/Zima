import Link from "next/link"
import { Shield } from "lucide-react"

export default function LegalLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <header className="border-b border-slate-800 px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5 w-fit">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-violet-600">
            <Shield className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-sm font-bold text-white">Zima</span>
        </Link>
      </header>
      <main className="max-w-3xl mx-auto px-6 py-12">{children}</main>
      <footer className="border-t border-slate-800 px-6 py-6 text-center">
        <div className="flex items-center justify-center gap-4 text-xs text-slate-600">
          <Link href="/privacy" className="hover:text-slate-400 transition-colors">
            Privacy Policy
          </Link>
          <span>·</span>
          <Link href="/terms" className="hover:text-slate-400 transition-colors">
            Terms of Service
          </Link>
          <span>·</span>
          <Link href="/" className="hover:text-slate-400 transition-colors">
            Back to Zima
          </Link>
        </div>
      </footer>
    </div>
  )
}
