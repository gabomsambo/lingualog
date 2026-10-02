import type React from "react"
import { Nunito } from "next/font/google"
import { Toaster } from "@/components/ui/toaster"
import { ThemeProvider } from "@/components/theme-provider"
import { LocaleProvider } from "@/i18n/LocaleProvider"
import { DevLanguageSwitcher } from "@/components/dev-language-switcher"

import "./globals.css"
// import "../i18n/i18n" // Temporarily disabled for testing

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
        <LocaleProvider>
          <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
            {children}
            <Toaster />
            <DevLanguageSwitcher />
          </ThemeProvider>
        </LocaleProvider>
        
      </body>
    </html>
  )
}
