"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { BookText, BarChart2, Bookmark } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

export function MainNav() {
  const pathname = usePathname()

  const routes = [
    {
      href: "/dashboard",
      label: "Dashboard",
      icon: <BookText className="mr-2 h-5 w-5" />,
      active: pathname === "/dashboard",
      variant: "green" as const,
    },
    {
      href: "/vocabulary",
      label: "Vocabulary",
      icon: <Bookmark className="mr-2 h-5 w-5" />,
      active: pathname === "/vocabulary",
      variant: "blue" as const,
    },
    {
      href: "/stats",
      label: "Statistics",
      icon: <BarChart2 className="mr-2 h-5 w-5" />,
      active: pathname === "/stats",
      variant: "purple" as const,
    },
  ]

  return (
    <nav className="hidden md:flex items-center space-x-4">
      {routes.map((route) => (
        <Button
          key={route.href}
          variant={route.active ? route.variant : "ghost"}
          asChild
          className={cn("justify-start text-base rounded-full", route.active ? "text-white" : "hover:bg-fun-purple/10")}
          size="sm"
        >
          <Link href={route.href} className="flex items-center">
            {route.icon}
            <span>{route.label}</span>
          </Link>
        </Button>
      ))}
    </nav>
  )
}
