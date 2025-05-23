import type React from "react"
import { Nunito } from "next/font/google"
import { Toaster } from "@/components/ui/toaster"
import { ThemeProvider } from "@/components/theme-provider"
import Script from "next/script"

import "./globals.css"

// Configure the Nunito font with all weights for a more rounded, playful look
const nunito = Nunito({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800", "900"],
  display: "swap",
  variable: "--font-nunito",
})

export const metadata = {
  title: "LinguaLog - Language Learning Journal",
  description: "Track your language learning journey with daily journaling and vocabulary tracking",
    generator: 'v0.dev'
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${nunito.className} font-playful min-h-screen`}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
          {children}
          <Toaster />
        </ThemeProvider>
        
        {/* API URL fix script */}
        <Script src="/fix-api.js" strategy="afterInteractive" />
      </body>
    </html>
  )
}
