import type React from "react"
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-fun-blue/10 via-fun-purple/10 to-fun-pink/10">
      <div className="w-full max-w-md">{children}</div>
    </div>
  )
}
